import sys
import os
import re
import md5
import urllib
import urllib2

# external deps
from BeautifulSoup import BeautifulSoup
import feedparser

import kaa.notifier
import kaa.beacon
import kaa.strutils

from download import fetch

for t in ('video', 'audio', 'image'):
    kaa.beacon.register_file_type_attrs(
        t, mediafeed_channel = (int, kaa.beacon.ATTR_SIMPLE))

pm = urllib2.HTTPPasswordMgrWithDefaultRealm()
auth_handler = urllib2.HTTPBasicAuthHandler(pm)
opener = urllib2.build_opener(auth_handler)
urllib2.install_opener(opener)

# ##################################################################
# some generic entry/channel stuff
# ##################################################################

IMAGEDIR = os.path.expanduser("~/.beacon/feedinfo/images")

if not os.path.isdir(IMAGEDIR):
    os.makedirs(IMAGEDIR)


class Entry(dict):

    def __getattr__(self, attr):
        if attr == 'basename' and not 'basename' in self.keys():
            self['basename'] = self['title'].replace('/', '') + '.' + self['ext']
        return self.get(attr)

    def fetch(self, filename):
        print '%s -> %s' % (self.url, filename)
        return fetch(self.url, filename)


class Channel(object):

    def __init__(self, url):
        self.url = url

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
        url = kaa.strutils.unicode_to_str(url)
        fname = md5.md5(url).hexdigest() + os.path.splitext(url)[1]
        fname = os.path.join(IMAGEDIR, fname)
        if os.path.isfile(fname):
            yield fname
        img = open(fname, 'w')
        img.write(urllib2.urlopen(url).read())
        img.close()
        yield img

    # update (download) feed

    @kaa.notifier.yield_execution()
    def update(self, destdir, num=0):
        def print_status(s):
            sys.stdout.write("%s\r" % str(s))
            sys.stdout.flush()

        for entry in self:
            if isinstance(entry, kaa.notifier.InProgress):
                # dummy entry to signal waiting
                yield entry
                continue
            num -= 1
            filename = os.path.join(destdir, entry.basename)
            # FIXME: download to tmp dir first
            async = entry.fetch(filename)
            async.get_status().connect(print_status, async.get_status())
            yield async
            # FIXME: add additional information to beacon
            if num == 0:
                return

    @kaa.notifier.yield_execution()
    def store_in_beacon(self, destdir, num):
        print 'update', self.url
        d = kaa.beacon.get(destdir)
        items = {}
        for i in d.list():
            if i.get('mediafeed_channel') == self.url:
                items[i.url] = i

        for entry in self:
            if isinstance(entry, kaa.notifier.InProgress):
                # dummy entry to signal waiting
                yield entry
                continue

            if entry.url in items:
                del items[entry.url]
            else:
                data = {}
                for key in ('url', 'title', 'description', 'image'):
                    if entry.get(key):
                        data[key] = entry[key]
                i = kaa.beacon.add_item(type='video', parent=d,
                                        mediafeed_channel=self.url, **data)
            num -= 1
            if num == 0:
                break

        for i in items.values():
            i.delete()

_generators = []

def register(regexp, generator):
    _generators.append((regexp, generator))

def get_channel(url):
    for regexp, generator in _generators:
        if regexp.match(url):
            return generator(url)
    raise RuntimeError

    
