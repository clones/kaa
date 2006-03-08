from kaa.base.strutils import str_to_unicode
import weakref, time

class Channel(object):
    def __init__(self, tuner_id, short_name, long_name, epg):
        self.db_id      = None
        self.tuner_id   = tuner_id
        self.short_name = short_name
        self.long_name  = long_name

        # kludge - remove
        self.id = short_name

        self._epg = weakref.ref(epg)

    def get_epg(self):
        return self._epg()

    def get_programs(self, t = None):
        if not t:
            t = time.time()

        return self.get_epg().search(time = t, channel = self)

