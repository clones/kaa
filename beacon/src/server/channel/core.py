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
from kaa.strutils import str_to_unicode, unicode_to_str

# get manager module
import manager

# get logging object
log = logging.getLogger('beacon.feed')

# ##################################################################
# some generic entry/feed stuff
# ##################################################################

IMAGEDIR = os.path.expanduser("~/.beacon/images")

if not os.path.isdir(IMAGEDIR):
    os.makedirs(IMAGEDIR)

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


class Feed(object):

    _db = None
    NEXT_ID = 0
    
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
        self.id = Feed.NEXT_ID
        Feed.NEXT_ID += 1
        

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
        manager.save()


    def get_config(self):
        """
        Get feed configuration.
        """
        return dict(id = self.id,
                    url = self.url,
                    directory = self.dirname,
                    download = self._download,
                    num = self._num,
                    keep = self._keep)
    
    def _readxml(self, node):
        """
        Read XML node with feed configuration and cache.
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
        Write XML node with feed configuration and cache.
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
            e = doc.createElement('entry')
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
        Update feed.
        """
        def print_status(s):
            sys.stdout.write("%s\r" % s.get_progressbar())
            sys.stdout.flush()

        log.info('update feed %s', self.url)

        # get directory information
        beacondir = self._db.query(filename=self.dirname)
        listing = beacondir.list()
        if isinstance(listing, kaa.notifier.InProgress):
            yield listing
            listing = listing.get_result()
        allurls = [ f.url for f in listing ]

        num = self._num
        allfiles = [ e[1] for e in self._entries ]
        entries = self._entries
        self._entries = []

        for entry in self:
            if isinstance(entry, kaa.notifier.InProgress):
                # dummy entry to signal waiting
                yield entry
                continue

            log.info('process %s', entry.url)
            filename = None

            if not self._download and entry.url in allurls:
                # already in beacon list
                pass
            elif not self._download:
                # add to beacon
                while self._db.read_lock.is_locked():
                    yield self._db.read_lock.yield_unlock()
                # use url as name
                entry['name'] = unicode_to_str(entry.url)
                i = self._db.add_object(parent=beacondir, **entry)
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
                    item = self._db.query(filename=filename)
                    if not item.scanned():
                        async = item.scan()
                        if isinstance(async, kaa.notifier.InProgress):
                            yield async
                    for key, value in entry.items():
                        if not key in ('type', 'url', 'basename'):
                            item[key] = value

            self._entries.append((entry['url'], filename))
            num -= 1
            if num == 0:
                break

        log.info('*** finished with %s ***', self.url)
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


    @kaa.notifier.yield_execution()
    def remove(self):
        """
        Remove entries from this feed.
        """
        log.info('remove %s', self.url)
        if self._keep or self._download:
            # only delete links in the filesystem
            return
            
        # get directory information
        beacondir = self._db.query(filename=self.dirname)
        allurls = [ e[0] for e in self._entries ]
        listing = beacondir.list()
        if isinstance(listing, kaa.notifier.InProgress):
            yield listing
            listing = listing.get_result()
        for entry in listing:
            if entry.url in allurls:
                log.info('delete %s', entry.url)
                entry.delete()
