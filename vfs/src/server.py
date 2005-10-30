import os
import stat

from kaa.base import ipc, weakref
from kaa.base.db import *
from kaa.notifier import Signal, OneShotTimer, Timer
import kaa.metadata

class Item(object):
    def __init__(self, data, parent, db):
        self.data = data
        self.parent = parent
        self.db = db

        # self.dirname always ends with a slash
        # if the item is a dir, self.filename also ends with a slash
        # self.url does not end with a slash (except root)
        
        # If parent is not set, this is a root node. A root node
        # is always part of the db already
        if not parent:
            self.url = 'file:/' + self.data['name']
            self.dirname = self.data['name']
            self.filename = self.data['name']
            self.isdir = True
            self.basename = '/'
            return

        if isinstance(self.data, dict):
            self.basename = self.data['name']
        else:
            self.basename = self.data

        # check if the item s based on a file
        if parent.filename:
            self.url = 'file:/' + parent.filename + self.basename
            self.dirname = parent.filename
            self.filename = parent.filename + self.basename
            if os.path.isdir(self.filename):
                self.filename += '/'
                self.isdir = True
            else:
                self.isdir = False
                    
        # TODO: handle files/parents not based on file:


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


#     def __del__(self):
#         print 'del %s' % self


def get_mtime(item):
    if not item.filename:
        print 'no filename == no mtime :('
        return 0

    mtime = 0
    if item.isdir:
        return os.stat(item.filename)[stat.ST_MTIME]

    # mtime is the the mtime for all files having the same
    # base. E.g. the mtime of foo.jpg is the sum of the
    # mtimeof foo.jpg and foo.jpg.xml or for foo.mp3 the
    # mtime is the sum of foo.mp3 and foo.jpg.
    
    base = os.path.splitext(item.filename)[0]
    
    # TODO: add overlay support
    
    # TODO: Make this much faster. We should cache the listdir
    # and the stat results somewhere, maybe already split by ext
    # But since this is done in background, this is not so
    # important right now.
    files = map(lambda x: item.dirname + x, os.listdir(item.dirname))
    for f in filter(lambda x: x.startswith(base), files):
        mtime += os.stat(f)[stat.ST_MTIME]
    return mtime
    

def parse(db, item):
    mtime = get_mtime(item)
    if not mtime:
        print 'oops, no mtime', item
        return
    attributes = { 'mtime': mtime }
    metadata = kaa.metadata.parse(item.filename)
    if isinstance(item.data, dict):
        type = item.data['type']
    elif metadata and metadata['media'] and \
             db._object_types.has_key(metadata['media']):
        type = metadata['media']
    elif item.isdir:
        type = 'dir'
    else:
        type = 'file'

    type_list = db._object_types[type]
    for key in type_list[1].keys():
        if metadata and metadata.has_key(key) and metadata[key] != None:
            attributes[key] = metadata[key]

    # TODO: do some more stuff here:
    # - check metadata for thumbnail or cover (audio) and use kaa.thumb to store it
    # - schedule thumbnail genereation with kaa.thumb
    # - search for covers based on the file (should be done by kaa.metadata)
    # - maybe the item is now in th db so we can't add it again
    if isinstance(item.data, dict):
        # update
        id = item.data['id']
        db.update_object((type, id), **attributes)
        item.data.update(attributes)
    else:
        # create
        item.data = db.add_object(type, name=item.basename,
                                  parent=item.parent.__id__(),
                                  **attributes)
    return True

class Checker(object):
    def __init__(self, db, items, progress, callback):
        self.db = db
        self.items = items
        self.max = len(items)
        self.pos = 0
        self.progress = progress
        self.callback = callback
        Timer(self.check).start(0.01)

    def check(self):
        if not self.items:
            self.db.commit()
            self.callback()
            return False
        self.pos += 1
        self.progress(self.pos, self.max)
        item = self.items[0]
        parse(self.db, item)
        self.items = self.items[1:]
        return True
    
class Query(object):
    def __init__(self, server, db, query):
        self._server = server
        self._db = db
        self._items = []
        self._query = query
        
    def __del__(self):
        print 'DEL'

    def check_query(self):
        need_update = []
        for i in self._items:
            if not i.filename:
                # FIXME: handle non file items
                pass
            elif not isinstance(i.data, dict):
                # Never scanned by the db
                need_update.append(i)
            elif get_mtime(i) != i.data['mtime']:
                # updated on disc
                need_update.append(i)
        self.progress(0, len(need_update))
        if need_update:
            Checker(self._db, need_update, self.progress, self.changed)

    def progress(self, pos, all):
        self._server.notify(self, 'progress', pos, all, __ipc_oneway=True)
        
    def changed(self):
        self._server.notify(self, 'changed', __ipc_oneway=True)
        
class DirectoryQuery(Query):
    def __init__(self, server, db, **kwargs):
        Query.__init__(self, server, db, kwargs)
        self.dir = server.get_dir(kwargs['dir'])
        
    def execute(self):
        self._items = []
        dirname = os.path.normpath(self.dir['url'][5:])
        files = self._db.query(parent = ("dir", self.dir["id"]))
        fs_listing = os.listdir(dirname)

        # TODO: add OVERLAY_DIR support
        # Ignore . files
        
        for f in files[:]:
            if f['name'] in fs_listing:
                # file still there
                fs_listing.remove(f['name'])
                self._items.append(Item(f, self.dir, self._db))
            else:
                # file deleted
                files.remove(f)
                # FIXME: remove from database

        for f in fs_listing:
            # new files
            self._items.append(Item(f, self.dir, self._db))
            
#         for i in self._items:
#             print i
        OneShotTimer(self.check_query).start(0.01)
        return self._items

        
class Server(object):
    def __init__(self, dbdir):
        if not os.path.isdir(dbdir):
            os.makedirs(dbdir)
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
            date = (unicode, ATTR_SEARCHABLE))

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
        self._active_queries = []

    def register_object_type_attrs(self, *args, **kwargs):
        return self._db.register_object_type_attrs(*args, **kwargs)

    
    def query(self, callback, **kwargs):
        if 'dir' in kwargs:
            query = DirectoryQuery(self, self._db, **kwargs)
        else:
            raise AttributeError('query not supported')
        self._active_queries.append((weakref(query), callback))
        return query
        
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

    def notify(self, object, *args, **kwargs):
        for local, remote in self._active_queries:
            if local == object:
#                 print 'found'
                remote(object._query, *args, **kwargs)
        pass
    
    def _client_closed(self, client):
        pass
#         for signal in self.signals.values():
#             for callback in signal:
#                 if ipc.get_ipc_from_proxy(callback) == client:
#                     signal.disconnect(callback)
