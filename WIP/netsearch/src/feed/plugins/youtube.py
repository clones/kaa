import re
from kaa.netsearch.feed.channel import Channel

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
