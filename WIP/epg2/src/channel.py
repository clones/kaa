from kaa.base.utils import str_to_unicode
import weakref, time

class Channel(object):
    def __init__(self, channel, station, name, epg):
        self.id = None
        self.channel = channel
        self.station = station
        self.name = name

        self._epg = weakref.ref(epg)

    def get_epg(self):
        return self._epg()

    def get_programs(self, t = None):
        if not t:
            t = time.time()

        return self.get_epg().search(time = t, channel = self)

