from kaa.strutils import str_to_unicode
import weakref, time

class Channel(object):
    def __init__(self, tuner_id, name, long_name, epg):
        self.db_id      = None
        self.tuner_id   = tuner_id
        self.name = name
        self.long_name  = long_name

        # kludge - remove
        self.id = name

        if epg:
            self._epg = weakref.ref(epg)
        else:
            self._epg = None

    def get_epg(self):
        return self._epg()

    def get_programs(self, t = None):
        if not t:
            t = time.time()

        if self._epg:
            return self.get_epg().search(time = t, channel = self)
        else:
            return []

