__all__ = [ 'medialist' ]

import os
import logging

from kaa.weakref import weakref

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


    def update(self, prop):
        self.prop = prop
        # FIXME: could str() crash?
        self.device = str(prop.get('block.device'))
        self.mountpoint = str(prop.get('volume.mount_point'))
        if not self.mountpoint:
            self.mountpoint = self.device
        if not self.mountpoint.endswith('/'):
            self.mountpoint += '/'
        self.overlay = os.path.join(self._db.dbdir, self.id)
        # FIXME: gc doesn't like that
        self._beacon_media = self
        # get basic information from database
        media, self._beacon_id, self.root = \
               self._db.query_media(self.id, self)
        prop['beacon.content'] = media['content']
        self._beacon_isdir = False
        if media['content'] == 'file':
            self._beacon_isdir = True
        self.thumbnails = os.path.join(self.overlay, '.thumbnails')
        if self.mountpoint == '/':
            self.thumbnails = os.path.join(os.environ['HOME'], '.thumbnails')
        
#     def __del__(self):
#         print 'del', self

    def get(self, key):
        return self.prop.get(key)

    def __getitem__(self, key):
        return self.prop[key]

    def __setitem__(self, key, value):
        self.prop[key] = value

    def __repr__(self):
        return '<kaa.beacon.Media %s>' % self.id

    
class MediaList(object):

    def __init__(self):
        self._dict = dict()
        self.db = None
        self.controller = None

        
    def connect(self, db, controller):
        for media in self._dict.keys()[:]:
            self.remove(media)
        self.db = db
        self.controller = controller

        
    def add(self, id, prop):
        if not self.db:
            raise RuntimeError('not connected to database')
        if id in self._dict:
            return self._dict.get(id)
        m = Media(id, self.db, self.controller, prop)
        self._dict[id] = m
        return m


    def remove(self, id):
        if not id in self._dict:
            log.error('%s not in list' % id)
            return None
        m = self._dict[id]
        del self._dict[id]
        return m
    
        
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
