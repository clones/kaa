import sys
import os
import re
import md5
import urllib
import urllib2
import logging
from xml.dom import minidom

# external deps
from BeautifulSoup import BeautifulSoup
import feedparser

# kaa imports
import kaa.notifier
import kaa.beacon
from kaa.strutils import str_to_unicode, unicode_to_str

from download import fetch

# get logging object
log = logging.getLogger('beacon')

pm = urllib2.HTTPPasswordMgrWithDefaultRealm()
auth_handler = urllib2.HTTPBasicAuthHandler(pm)
opener = urllib2.build_opener(auth_handler)
urllib2.install_opener(opener)

# ##################################################################
# some generic entry/channel stuff
# ##################################################################

IMAGEDIR = os.path.expanduser("~/.beacon/feedinfo/images")
CACHEDIR = os.path.expanduser("~/.beacon/feedinfo")

if not os.path.isdir(IMAGEDIR):
    os.makedirs(IMAGEDIR)


class Entry(dict):

    def __getattr__(self, attr):
        if attr == 'basename' and not 'basename' in self.keys():
            self['basename'] = self['title'].replace('/', '') + '.' + self['ext']
        return self.get(attr)

    def fetch(self, filename):
        log.info('%s -> %s' % (self.url, filename))
        return fetch(self.url, filename)


class Channel(object):

    def __init__(self, url, destdir):
        self.url = url
        self._destdir = destdir
        self._cache = os.path.join(CACHEDIR, md5.md5(url).hexdigest() + '.xml')
        self.configure()
        self._entries = []

        if not os.path.isdir(destdir):
            os.makedirs(destdir)

    def configure(self, download=True, num=0, keep=0):
        """
        Configure feed
        num:      number of items from the feed (0 == all, default)
        keep:     keep old entries not in feed anymore (download only)
        verbose:  print status on stdout
        """
        self._download = download
        self._num = num
        self._keep = keep


    def append(self):
        if os.path.isfile(self._cache):
            raise RuntimeError()
        _channels.append(self)
        self._writexml()

    # state information
    def _readxml(self, nodes):
        for node in nodes:
            if node.nodeName == 'entry':
                fname = unicode_to_str(node.getAttribute('filename')) or None
                self._entries.append((node.getAttribute('url'), fname))

    def _writexml(self):
        doc = minidom.getDOMImplementation().createDocument(None, "feed", None)
        top = doc.documentElement
        top.setAttribute('url', self.url)
        d = doc.createElement('directory')
        for attr in ('download', 'keep'):
            if getattr(self, '_' + attr):
                d.setAttribute(attr, 'true')
            else:
                d.setAttribute(attr, 'false')
            d.setAttribute('num', str(self._num))
        d.appendChild(doc.createTextNode(self._destdir))
        top.appendChild(d)
        for url, fname in self._entries:
            e = doc.createElement('entry')
            e.setAttribute('url', url)
            if fname:
                e.setAttribute('filename', str_to_unicode(fname))
            top.appendChild(e)
        f = open(self._cache, 'w')
        f.write(doc.toprettyxml())
        f.close()

    # Some internal helper functions

    def _thread(self, *args, **kwargs):
        t = kaa.notifier.Thread(*args, **kwargs)
        t.wait_on_exit(False)
        self._async = t.start()
        return self._async

    def _feedparser(self, url):
        return self._thread(feedparser.parse, urllib2.urlopen(url))

    def _beautifulsoup(self, url):
        def __beautifulsoup(url):
            return BeautifulSoup(urllib2.urlopen(url))
        return self._thread(__beautifulsoup, url)

    def _readurl(self, url):
        def __readurl(url):
            return urllib2.urlopen(url).read()
        return self._thread(__readurl, url)

    def _get_result(self):
        return self._async.get_result()

    @kaa.notifier.yield_execution()
    def _get_image(self, url):
        url = unicode_to_str(url)
        fname = md5.md5(url).hexdigest() + os.path.splitext(url)[1]
        fname = os.path.join(IMAGEDIR, fname)
        if os.path.isfile(fname):
            yield fname
        img = open(fname, 'w')
        img.write(urllib2.urlopen(url).read())
        img.close()
        yield img

    @kaa.notifier.yield_execution()
    def update(self, verbose=False):
        """
        Update feed.
        """
        def print_status(s):
            sys.stdout.write("%s\r" % str(s))
            sys.stdout.flush()

        # get directory information
        beacondir = kaa.beacon.get(self._destdir)
        allurls = [ f.url for f in beacondir.list() ]

        num = self._num
        allfiles = [ e[1] for e in self._entries ]
        entries = self._entries
        self._entries = []

        for entry in self:
            if isinstance(entry, kaa.notifier.InProgress):
                # dummy entry to signal waiting
                yield entry
                continue

            # create additional information
            info = {}
            for key in ('title', 'description', 'image'):
                if entry.get(key):
                    info[key] = entry[key]
            filename = None

            if not self._download and entry.url in allurls:
                # already in beacon list
                pass
            elif not self._download:
                # add to beacon
                info['url'] = entry['url']
                i = kaa.beacon.add_item(
                    type='video', parent=beacondir,
                    mediafeed_channel=self.url, **info)
            else:
                # download
                filename = os.path.join(self._destdir, entry.basename)
                if not os.path.isfile(filename) and filename in allfiles:
                    # file not found, check if it was downloaded before. If
                    # so, the user deleted it and we do not fetch it again
                    continue
                if os.path.isfile(filename):
                    # File already downloaded.
                    # FIXME: make sure the file is up-to-date
                    continue
                async = entry.fetch(filename)
                if verbose:
                    async.get_status().connect(print_status, async.get_status())
                # FIXME: add additional information to beacon
                yield async

            self._entries.append((entry['url'], filename))
            num -= 1
            if num == 0:
                break

        self._writexml()

        # delete old files or remove old entries from beacon
        for url, filename in entries:
            if (self._keep and self._download) or (url, filename) in self._entries:
                continue
            if not filename:
                # delete old entries from beacon
                for f in beacondir.list():
                    if f.url == url:
                        f.delete()
            elif os.path.isfile(filename):
                # delete file on disc
                os.unlink(filename)

_generators = []

def register(regexp, generator):
    _generators.append((regexp, generator))

def get_channel(url, destdir):
    for regexp, generator in _generators:
        if regexp.match(url):
            return generator(url, destdir)
    raise RuntimeError

_channels = []

def init():
    for f in os.listdir(CACHEDIR):
        if not f.endswith('.xml'):
            continue
        try:
            c = minidom.parse(os.path.join(CACHEDIR, f))
        except:
            log.error('bad cache file: %s' % f)
            continue
        if not len(c.childNodes) == 1 or not c.childNodes[0].nodeName == 'feed':
            log.error('bad cache file: %s' % f)
            continue
        url = c.childNodes[0].getAttribute('url')
        channel = None
        for d in c.childNodes[0].childNodes:
            if d.nodeName == 'directory':
                dirname = unicode_to_str(d.childNodes[0].data.strip())
                channel = get_channel(url, dirname)
                channel.configure(
                    d.getAttribute('download').lower() == 'true',
                    int(d.getAttribute('num')),
                    d.getAttribute('keep').lower() == 'true')
                channel._readxml(c.childNodes[0].childNodes)
                _channels.append(channel)
                break
        if not channel:
            log.error('bad cache file: %s' % f)
            continue

@kaa.notifier.yield_execution()
def update(verbose=False):
    for channel in _channels:
        yield channel.update(verbose=verbose)
