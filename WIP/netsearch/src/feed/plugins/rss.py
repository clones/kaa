import re
import logging

import kaa.notifier

from kaa.netsearch.feed.lib import feedparser
from kaa.netsearch.feed.channel import Channel
from kaa.netsearch.feed.manager import register

# get logging object
log = logging.getLogger('beacon.feed')

class RSS(Channel):

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
            if 'link' in f.keys():
                link = f.link
            if 'enclosures' in f.keys():
                # FIXME: more details than expected
                if len(f.enclosures) > 1:
                    log.warning('more than one enclosure in %s' % self.url)
                link = f.enclosures[0].href
            # FIXME: add much better logic here, including
            # getting a good basename for urls ending with /
            # based on type.
            if not link:
                log.error('no link in entry for %s' % self.url)
                continue
            # create entry
            entry = Channel.Entry(basename=link[link.rfind('/')+1:], url=link,
                                  description=f.get('summary', ''), image=feedimage)
            if 'title' in f:
                entry['title'] = f['title']
            yield entry

register(re.compile('^https?://.*'), RSS)
