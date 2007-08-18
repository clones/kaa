import sys
import kaa.notifier
from kaa.netsearch.feed import Channel

# ##################################################################
# test code
# ##################################################################

# class Filter(Channel):

#     def __init__(self, channel, filter):
#         Channel.__init__(self, None)
#         self._channel = channel
#         self._filter = filter

#     def __iter__(self):
#         for f in self._channel:
#             if isinstance(f, kaa.notifier.InProgress):
#                 # dummy entry to signal waiting
#                 yield f
#                 continue
#             if self._filter(f):
#                 yield f

@kaa.notifier.yield_execution()
def update_feeds(*feeds):
    for feed, destdir, num, download in feeds:
        if download:
            yield feed.update(destdir, num)
        else:
            yield feed.store_in_beacon(destdir, num)

kaa.beacon.connect()
d = '/local/video/feedtest'
update_feeds((Channel('http://podcast.wdr.de/blaubaer.xml'), d, 5, False),
             (Channel('http://podcast.nationalgeographic.com/wild-chronicles/'), \
              d, 5, False)).\
             connect(sys.exit)
#              (Channel('http://www.tagesschau.de/export/video-podcast'), d, 1, False),
#              (YouTube(tags='robot chicken'), d, 2, True),
#              (Stage6('stage6://Diva-Channel'), d, 5, False)).\

kaa.notifier.loop()

