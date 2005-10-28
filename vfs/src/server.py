import os

from kaa.base import ipc
from kaa.base.db import *
from kaa.notifier import Signal

class Item(object):
    def __init__(self, data, parent, db):
        self.data = data
        self.parent = parent
        self.db = db
        if isinstance(self.data, dict) and parent and parent.isdir():

            # TODO: handle parents not based on file:

            if self.parent['url'] == 'file:/':
                self.data['url'] = 'file:/' + self.data['name']
            else:
                self.data['url'] = self.parent['url'] + '/' + self.data['name']
        self.__changes = {}


    def __id__(self):
        return (self.data['type'], self.data["id"])
    

    def __str__(self):
        if isinstance(self.data, str):
            return 'new file %s' % self.data
        return self.data['name']


    def __getitem__(self, key):
        if self.data.has_key(key):
            return self.data[key]
        if self.data.has_key('tmp:' + key):
            return self.data['tmp:' + key]

        # TODO: maybe get cover from parent (e.g. cover in a dir)
        # Or should that be stored in each item
        
        return None


    def isdir(self):
        if isinstance(self.data, (str, unicode)):
            return os.path.isdir(self.parent['url'][5:] + '/' + self.data)
        return self.data['type'] == 'dir'

    


class Query(object):
    def __init__(self, db):
        self._db = db
        self.items = []

class DirectoryQuery(Query):
    def __init__(self, server, db, **kwargs):
        Query.__init__(self, db)
        self.dir = server.get_dir(kwargs['dir'])
        
        dirname = os.path.normpath(self.dir['url'][5:])
        files = self._db.query(parent = ("dir", self.dir["id"]))
        fs_listing = os.listdir(dirname)

        # TODO: add OVERLAY_DIR support
        # Ignore . files
        
        for f in files[:]:
            if f['name'] in fs_listing:
                # file still there
                fs_listing.remove(f['name'])
                self.items.append(Item(f, self, self._db))
            else:
                # file deleted
                files.remove(f)
                # FIXME: remove from database

        for f in fs_listing:
            # new files
            self.items.append(Item(f, self, self._db))
            
        for i in self.items:
            print i
        print 'DONE'
        
class Server(object):
    def __init__(self, dbdir):
        self.signals = {
            "updated": Signal(),
        }

        self._db = Database(dbdir + '/db')

        self.register_object_type_attrs("dir",
            name = (str, ATTR_KEYWORDS),
            mtime = (int, ATTR_SIMPLE))

        self.register_object_type_attrs("file",
            name = (str, ATTR_KEYWORDS),
            mtime = (int, ATTR_SIMPLE))

        self.register_object_type_attrs("video",
            name = (str, ATTR_KEYWORDS),
            mtime = (int, ATTR_SIMPLE),
            title = (unicode, ATTR_KEYWORDS),
            width = (int, ATTR_SIMPLE),
            height = (int, ATTR_SIMPLE),
            length = (int, ATTR_SIMPLE))

        self.register_object_type_attrs("audio",
            name = (str, ATTR_KEYWORDS),
            mtime = (int, ATTR_SIMPLE),
            title = (unicode, ATTR_KEYWORDS),
            artist = (unicode, ATTR_KEYWORDS | ATTR_INDEXED),
            album = (unicode, ATTR_KEYWORDS),
            genre = (unicode, ATTR_INDEXED),
            samplerate = (int, ATTR_SIMPLE),
            length = (int, ATTR_SIMPLE),
            bitrate = (int, ATTR_SIMPLE),
            trackno = (int, ATTR_SIMPLE))
        
        self.register_object_type_attrs("image",
            name = (str, ATTR_KEYWORDS),
            mtime = (int, ATTR_SIMPLE),
            width = (int, ATTR_SEARCHABLE),
            height = (int, ATTR_SEARCHABLE),
            date = (int, ATTR_SEARCHABLE))

        # TODO: add more known types
        
        root = self._db.query(type="dir", name="/")
        if not root:
            root = self._db.add_object("dir", name="/")
            # FIXME: get current data from database
            root = self._db.query(type='dir', name='/')[0]
        else:
            root = root[0]
        root['url'] = 'file:/'
        root = Item(root, None, self._db)
        self._dir_cache = { '/': root }
        self._parent_cache = { root.__id__(): root }
        
        self._ipc = ipc.IPCServer('vfs')
        self._ipc.signals["client_closed"].connect_weak(self._client_closed)
        self._ipc.register_object(self, "vfs")


    def register_object_type_attrs(self, *args, **kwargs):
        return self._db.register_object_type_attrs(*args, **kwargs)

    
    def query(self, **kwargs):
        if 'dir' in kwargs:
            return DirectoryQuery(self, self._db, **kwargs)
        raise AttributeError('query not supported')

        
    def get_dir(self, dirname):
        if dirname in self._dir_cache:
            return self._dir_cache[dirname]
        pdir = self.get_dir(os.path.dirname(dirname))
        print pdir
        parent = ("dir", pdir["id"])

        # TODO: handle dirs on romdrives which don't have '/'
        # as basic parent
        
        name = os.path.basename(dirname)
        current = self._db.query(type="dir", name=name, parent=parent)
        if not current:
            current = self._db.add_object("dir", name=name, parent=parent)
        else:
            current = current[0]
        current['url'] = 'file:' + dirname
        current = Item(current, pdir, self._db)
        self._dir_cache[dirname] = current
        self._parent_cache[current.__id__()] = current
        return current

        
    def _client_closed(self, client):
        for signal in self.signals.values():
            for callback in signal:
                if ipc.get_ipc_from_proxy(callback) == client:
                    signal.disconnect(callback)
