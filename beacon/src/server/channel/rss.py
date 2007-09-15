import re
import time
import logging
import urllib2

import kaa.notifier

import feedparser as _feedparser
import feed

# get logging object
log = logging.getLogger('beacon.feed')
isotime = '%a, %d %b %Y %H:%M:%S'

@kaa.notifier.execute_in_thread()
def feedparser(url):
    return _feedparser.parse(urllib2.urlopen(url))

class Feed(feed.Feed):

    def __iter__(self):
        # get feed in a thread
        feed = feedparser(self.url)
        yield feed
        feed = feed.get_result()

        if not feed.entries:
            log.error('no entries in %s' % self.url)
            raise StopIteration

        # basic information
        feedimage = None
        if feed.feed.get('image'):
            feedimage = feed.feed.get('image').get('href')

        if feedimage:
            # FIXME: beacon does not thumbnail the image without
            # a rescan of the directory!
            feedimage = self._get_image(feedimage)
            if isinstance(feedimage, kaa.notifier.InProgress):
                yield feedimage
                feedimage = feedimage.get_result()

        # real iterate
        for f in feed.entries:

            metadata = {}

            if feedimage:
                metadata['image'] = feedimage
            if 'updated' in f.keys():
                date = f.updated
                if date.find('+') > 0:
                    date = date[:date.find('+')].strip()
                if date.rfind(' ') > date.rfind(':'):
                    date = date[:date.rfind(' ')]
                try:
                    metadata['date'] = int(time.mktime(time.strptime(date, isotime)))
                except ValueError:
                    log.error('bad date format: %s', date)
                    
            if 'itunes_duration' in f.keys():
                duration = 0
                for p in f.itunes_duration.split(':'):
                    duration = duration * 60 + int(p)
                metadata['length'] = duration
            if 'summary' in f.keys():
                metadata['description']=f.summary
            if 'title' in f.keys():
                metadata['title'] = f.title
                
            if 'enclosures' in f.keys():
                # FIXME: more details than expected
                if len(f.enclosures) > 1:
                    log.warning('more than one enclosure in %s' % self.url)
                metadata['url'] = f.enclosures[0].href
                for ptype in ('video', 'audio', 'image'):
                    if f.enclosures[0].type.startswith(ptype):
                        metadata['type'] = ptype
                        break
            elif 'link' in f.keys():
                # bad RSS style
                metadata['url'] = f.link
            else:
                log.error('no link in entry for %s' % self.url)
                continue

            # FIXME: add much better logic here, including
            # getting a good basename for urls ending with /
            # based on type.
            # create entry
            entry = feed.Entry(**metadata)
            yield entry
