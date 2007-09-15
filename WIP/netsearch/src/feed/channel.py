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

# get manager module
import manager

# get logging object
log = logging.getLogger('beacon.channel')

# ##################################################################
# some generic entry/channel stuff
# ##################################################################

IMAGEDIR = os.path.expanduser("~/.beacon/images")

if not os.path.isdir(IMAGEDIR):
    os.makedirs(IMAGEDIR)

class Channel(object):

    class Entry(dict):

        def __getattr__(self, attr):
            if attr == 'basename' and not 'basename' in self.keys():
                basename = os.path.basename(self['url'])
                if self.url.endswith('/'):
                    ext = os.path.splitext(self['url'])[1]
                    basename = self['title'].replace('/', '') + ext
                self['basename'] = unicode_to_str(basename)
            return self.get(attr)

        def fetch(self, filename):
            log.info('%s -> %s' % (self.url, filename))
            tmpname = os.path.join(os.path.dirname(filename),
                                   '.' + os.path.basename(filename))
            return kaa.notifier.url.fetch(self.url, filename, tmpname)


    def __init__(self, url, destdir):
        self.url = url
        self.dirname = destdir
        self._manager = manager
        self._entries = []
        self._download = True
        self._num = 0
        self._keep = True
        if not os.path.isdir(destdir):
            os.makedirs(destdir)


    def configure(self, download=True, num=0, keep=True):
        """
        Configure channel
        num:      number of items from the channel (0 == all, default)
        keep:     keep old entries not in channel anymore (download only)
        verbose:  print status on stdout
        """
        self._download = download
        self._num = num
        self._keep = keep
        manager.save()


    def _readxml(self, node):
        """
        Read XML node with channel configuration and cache.
        """
        for d in node.childNodes:
            if not d.nodeName == 'directory':
                continue
            self._download = d.getAttribute('download').lower() == 'true'
            self._num = int(d.getAttribute('num'))
            self._keep = d.getAttribute('keep').lower() == 'true'
            for node in d.childNodes:
                if not node.nodeName == 'entry':
                    continue
                fname = unicode_to_str(node.getAttribute('filename')) or None
                self._entries.append((node.getAttribute('url'), fname))


    def _writexml(self, node):
        """
        Write XML node with channel configuration and cache.
        """
        node.setAttribute('url', self.url)
        doc = node.ownerDocument
        d = doc.createElement('directory')
        for attr in ('download', 'keep'):
            if getattr(self, '_' + attr):
                d.setAttribute(attr, 'true')
            else:
                d.setAttribute(attr, 'false')
            d.setAttribute('num', str(self._num))
        d.appendChild(doc.createTextNode(self.dirname))
        node.appendChild(d)
        for url, fname in self._entries:
            e = node.createElement('entry')
            e.setAttribute('url', url)
            if fname:
                e.setAttribute('filename', str_to_unicode(fname))
            node.appendChild(e)


    @kaa.notifier.yield_execution()
    def _get_image(self, url):
        """
        Download image and store it to the image dir. Returns image
        filename.
        """
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
        Update channel.
        """
        def print_status(s):
            sys.stdout.write("%s\r" % s.get_progressbar())
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

            filename = None

            if not self._download and entry.url in allurls:
                # already in beacon list
                pass
            elif not self._download:
                # add to beacon
                i = kaa.beacon.add_item(parent=beacondir, **entry)
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
                    yield async
                    if not os.path.isfile(filename):
                        log.error('error fetching', entry.url)
                        continue
                    
                if os.path.isfile(filename):
                    item = kaa.beacon.get(filename)
                    if not item.scanned():
                        # BEACON_FIXME
                        item._beacon_request()
                        while not item.scanned():
                            yield kaa.notifier.YieldContinue
                    for key, value in entry.items():
                        if not key in ('type', 'url', 'basename'):
                            item[key] = value
                        
            self._entries.append((entry['url'], filename))
            num -= 1
            if num == 0:
                break

        manager.save()

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
