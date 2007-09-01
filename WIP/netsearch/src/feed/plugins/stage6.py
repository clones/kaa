import re
from kaa.netsearch.feed.channel import Channel

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
                # FIXME: grab the side of the video to get the tags of this
                # clip and an image
                vid = Stage6.match_video(url.get('href')).groups()[0]
                vurl = url='http://video.stage6.com/%s/.divx' % vid
                yield Entry(id=vid, title=title, ext='divx', url=vurl)
