import sys
import os
import re
import md5
import urllib
import urllib2
import logging
from xml.dom import minidom

# kaa imports
import kaa.notifier
import kaa.notifier.url
import kaa.beacon
from kaa.strutils import str_to_unicode, unicode_to_str

# get logging object
log = logging.getLogger('beacon.feed')

# ##################################################################
# some generic entry/channel stuff
# ##################################################################

IMAGEDIR = os.path.expanduser("~/.beacon/feedinfo/images")

if not os.path.isdir(IMAGEDIR):
    os.makedirs(IMAGEDIR)

class Channel(object):

    class Entry(dict):

        def __getattr__(self, attr):
            if attr == 'basename' and not 'basename' in self.keys():
                self['basename'] = self['title'].replace('/', '') + '.' + self['ext']
            return self.get(attr)

        def fetch(self, filename):
            log.info('%s -> %s' % (self.url, filename))
            tmpname = os.path.join(os.path.dirname(filename),
                                   '.' + os.path.basename(filename))
            return kaa.notifier.url.fetch(self.url, filename, tmpname)


    def __init__(self, url, destdir, cachefile):
        self.url = url
        self.dirname = destdir
        self._cache = cachefile
        self._entries = []
        self._download = True
        self._num = 0
        self._keep = True
        if not os.path.isdir(destdir):
            os.makedirs(destdir)


    def configure(self, download=True, num=0, keep=True):
        """
        Configure feed
        num:      number of items from the feed (0 == all, default)
        keep:     keep old entries not in feed anymore (download only)
        verbose:  print status on stdout
        """
        self._download = download
        self._num = num
        self._keep = keep
        self._writexml()


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
        d.appendChild(doc.createTextNode(self.dirname))
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


    @kaa.notifier.yield_execution()
    def _get_image(self, url):
        url = unicode_to_str(url)
        fname = md5.md5(url).hexdigest() + os.path.splitext(url)[1]
        fname = os.path.join(IMAGEDIR, fname)
        if os.path.isfile(fname):
            yield fname
        yield kaa.notifier.url.fetch(url, fname)
        yield fname


    @kaa.notifier.yield_execution()
    def update(self, verbose=False):
        """
        Update feed.
        """
        def print_status(s):
            sys.stdout.write("%s\r" % str(s))
            sys.stdout.flush()

        # get directory information
        beacondir = kaa.beacon.get(self.dirname)
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
                filename = os.path.join(self.dirname, entry.basename)
                if not os.path.isfile(filename) and filename in allfiles:
                    # file not found, check if it was downloaded before. If
                    # so, the user deleted it and we do not fetch it again
                    pass
                elif os.path.isfile(filename):
                    # File already downloaded.
                    # FIXME: make sure the file is up-to-date
                    pass
                else:
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
