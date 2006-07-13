__all__ = [ 'medialist' ]

import os
import logging

# get logging object
log = logging.getLogger('beacon.hwmon')

class Media(object):

    # check what mounpoint needs right now

    def __init__(self, id, db, controller, prop):
        self._db = db
        self._controller = controller
        self.id = id
        self.update(prop)

        # needed by server. FIXME: make it nicer
        self.crawler = None
        
        log.info('new mountpoint %s', self.id)

        # when we are here the media is in the database and also
        # the item for it

    def _beacon_controller(self):
        """
        Get the controller (the client or the server)
        """
        return self._controller

    
    def eject(self):
        self._controller.eject(self)


    def get_item(self):
        # return our root item (dir or item)
        # FIXME: do we need this?
        pass


    def update(self, prop):
        self.prop = prop
        # FIXME: could str() crash?
        self.device = str(prop.get('block.device'))
        self.mountpoint = str(prop.get('volume.mount_point'))
        if not self.mountpoint:
            self.mountpoint = self.device
        if not self.mountpoint.endswith('/'):
            self.mountpoint += '/'
        media = self._db.query_raw(type="media", name=self.id)[0]
        self._beacon_id = ('media', media['id'])
        self.url = media['content'] + '//' + self.mountpoint
        self.overlay = os.path.join(self._db.dbdir, self.id)
        # FIXME: do this directly in hwmon?
        if not os.path.isdir(self.overlay):
            os.mkdir(self.overlay)
        # FIXME: add .thumbnail dir
        
    def __del__(self):
        print 'del', self

    def __getattr__(self, attr):
        return getattr(self.prop, attr)

    def __repr__(self):
        return '<kaa.beacon.Media %s>' % self.id

    
class MediaList(object):

    def __init__(self):
        self._dict = dict()

        
    def add(self, id, db, controller, prop):
        if id in self._dict:
            return self._dict.get(id)
        m = Media(id, db, controller, prop)
        self._dict[id] = m
        return m


    def remove(self, id):
        if not id in self._dict:
            log.error('%s not in list' % id)
            return
        del self._dict[id]

        
    def get(self, id):
        return self._dict.get(id)


    def mountpoint(self, dirname):
        if not dirname.endswith('/'):
            dirname += '/'
        all = self._dict.values()[:]
        all.sort(lambda x,y: -cmp(x.mountpoint, y.mountpoint))
        for m in all:
            if dirname.startswith(m.mountpoint):
                return m
        return None

    
    def beacon_id(self, id):
        for m in self._dict.values():
            if m._beacon_id == id:
                return m
        return None

        
    def __iter__(self):
        return self._dict.values().__iter__()
    

medialist = MediaList()
