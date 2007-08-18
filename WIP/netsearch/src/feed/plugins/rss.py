import re
import kaa.notifier
from kaa.netsearch.feed.channel import Channel, Entry, register


class RSS(Channel):

    def __iter__(self):
        # get feed in a thread
        yield self._feedparser(self.url)
        if not self._get_result().entries:
            print 'oops'
            raise StopIteration

        # basic information
        feedimage = None
        if self._get_result().feed.get('image'):
            feedimage = self._get_result().feed.get('image').get('href')

        if feedimage:
            feedimage = self._get_image(feedimage)
            if isinstance(feedimage, kaa.notifier.InProgress):
                yield feedimage
                feedimage = feedimage.get_result()

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
            # FIXME: beacon does not thumbnail the image without
            # a rescan of the directory!
            entry = Entry(basename=link[link.rfind('/')+1:], url=link,
                          description=f.get('summary', ''), image=feedimage)
            if 'title' in f:
                entry['title'] = f['title']
            yield entry

register(re.compile('^https?://.*'), RSS)
