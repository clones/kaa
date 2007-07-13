import sys
import os
import re
import urllib
import urllib2

# external deps
from BeautifulSoup import BeautifulSoup
import feedparser

import kaa.notifier

# ##################################################################
# Brain Dump
#
# - Improve RSS channel for better video and audio feed support
#   https://channelguide.participatoryculture.org/front
# - Flickr image channel
# - Torrent downloader (needed for some democracy channels)
# - Add more item metadata (e.g. download thumbnail/image)
# - Channel configuration:
#   o always download / download on demand / play from stream
#   o how much entries should be show
#   o keep entries on hd (while in feed / while not watched / up to x)
# - Add parallel download function
# - Add channel as 'file' to kaa.beacon making it possible to merge
#   feed entries and real files.
#   o does it belong into beacon?
#   o is it an extra kaa module with beacon plugin?
#   o daemon to keep feeds in beacon up-to-date
#
# ##################################################################


# ##################################################################
# generic status object for InProgress
# ##################################################################

class Status(kaa.notifier.Signal):
    def __init__(self):
        super(Status,self).__init__()
        self.percent = 0
        self.pos = 0
        self.max = 0

    def set(self, pos, max=None):
        if max is not None:
            self.max = max
        self.pos = pos
        if pos > self.max:
            self.max = pos
        if self.max:
            self.percent = (self.pos * 100) / self.max
        else:
            self.percent = 0
        self.emit()

    def update(self, diff):
        self.set(self.pos + diff)


    def __str__(self):
        n = 0
        if self.max:
            n = int((self.pos / float(self.max)) * 50)
        return "|%51s| %d / %d" % (("="*n + ">").ljust(51), self.pos, self.max)


# ##################################################################
# function to download to a file with status information
# ##################################################################

def fetch_HTTP(url, filename):
    def download(url, filename, status):
        src = urllib2.urlopen(url)
        dst = open(filename, 'w')
        status.set(0, int(src.info().get('Content-Length', 0)))
        while True:
            data = src.read(1024)
            if len(data) == 0:
                src.close()
                dst.close()
                return True
            status.update(len(data))
            dst.write(data)

    s = Status()
    t = kaa.notifier.Thread(download, url, filename, s)
    t.wait_on_exit(False)
    async = t.start()
    async.set_status(s)
    return async


# ##################################################################
# some generic entry/channel stuff
# ##################################################################

class Entry(dict):

    def __getattr__(self, attr):
        if attr == 'basename' and not 'basename' in self.keys():
            self['basename'] = self['title'].replace('/', '') + '.' + self['ext']
        return self.get(attr)

    def fetch(self, filename):
        print '%s -> %s' % (self.url, filename)
        return fetch_HTTP(self.url, filename)


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
        return self._thread(feedparser.parse, url)

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
            if os.path.isfile(filename):
                print 'skip', filename
            else:
                async = entry.fetch(filename)
                async.get_status().connect(print_status, async.get_status())
                yield async
            if num == 0:
                return


# ##################################################################
# specific channels
# ##################################################################

class RSS(Channel):

    def __iter__(self):
        # get feed in a thread
        yield self._feedparser(self.url)

        if not self._get_result().entries:
            print 'oops'
            raise StopIteration

        # real iterate
        for f in self._get_result().entries:
            if 'link' in f.keys():
                link = f.link
            if 'enclosures' in f.keys():
                # FIXME: more details than expected
                if len(f.enclosures) > 1:
                    print 'WARNING:', f.enclosures
                link = f.enclosures[0].href
            # FIXME: add much better logic here, including
            # getting a good basename for urls ending with /
            # based on type.
            if not link:
                print 'WARNING', f
            entry = Entry(basename=link[link.rfind('/')+1:], url=link)
            # FIXME: description, etc missing
            if 'title' in f:
                entry['title'] = f['title']
            yield entry


class Stage6(Channel):

    match_video = re.compile('.*/video/([0-9]+)/').match

    def __iter__(self):
        baseurl = 'http://stage6.divx.com/%s/videos/order:date' % self.url
        counter = 0
        while True:
            counter += 1
            url = baseurl
            if counter > 1:
                url = baseurl + '?page=%s' % counter

            # get page in a thread
            yield self._beautifulsoup(url)
            hits = self._get_result().findAll(
                'a', href=lambda(v): Stage6.match_video(unicode(v)))
            if not len(hits):
                raise StopIteration

            # iterate over the hits on the page
            for url in hits:
                title = url.get('title')
                if not title:
                    continue
                # We could grab the side of the video to get the tags of this
                # clip but maybe it costs too much time.
                vid = Stage6.match_video(url.get('href')).groups()[0]
                vurl = url='http://video.stage6.com/%s/.divx' % vid
                yield Entry(id=vid, title=title, ext='divx', url=vurl)


class YouTube(Channel):

    def __init__(self, tags):
        url = 'http://www.youtube.com/rss/tag/%s.rss' % urllib.quote(tags)
        super(YouTube, self).__init__(url)

    def __iter__(self):
        # get feed in a thread
        yield self._feedparser(self.url)

        # real iterate
        for f in self._get_result().entries:
            yield self._readurl(f.id)
            m = re.search('"/player2.swf[^"]*youtube.com/&([^"]*)', self._get_result())
            url = 'http://youtube.com/get_video?' + m.groups()[0]
            yield Entry(url=url, title=f.title, ext='flv')


# ##################################################################
# test code
# ##################################################################

class Filter(Channel):

    def __init__(self, channel, filter):
        Channel.__init__(self, None)
        self._channel = channel
        self._filter = filter

    def __iter__(self):
        for f in self._channel:
            if isinstance(f, kaa.notifier.InProgress):
                # dummy entry to signal waiting
                yield f
                continue
            if self._filter(f):
                yield f

# c = Stage6('Diva-Channel')
# f = Filter(c, lambda(e): 'Lisa Loeb' in e.title)
# f.update('/local/video')

# f = Stage6('Diva-Channel')
# f.update('/local/video/MusicVideo', 2)

f = RSS('http://www.tagesschau.de/export/video-podcast')
f.update('/local/video', 2).connect(sys.exit)

# f = YouTube(tags='robot chicken')
# f.update('/local/video', 2)

kaa.notifier.loop()
