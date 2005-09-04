import os
import stat

import kaa.metadata

from db import *

class Listing(list):

    # TODO: add signals to the object, like 'changed'
    # The update function should run in background and should call
    # the changed signal at the end if one or more iitems returned
    # True for _parse
    
    def update(self):
        for i in self:
            i._parse()


    def __str__(self):
        ret = 'Listing\n'
        for i in self:
            ret += '  %s\n' % i
        return ret

    # TODO: The Listing should know the query it was based on
    # and should update itself.

    
class Item(object):
    def __init__(self, data, parent, db):
        self.data = data
        self.parent = parent
        self.db = db
        if isinstance(self.data, dict) and parent and parent.isdir():
            self.data['path'] = self.parent['path'] + '/' + self.data['name']
        self.__changes = {}

        
    def _parse(self):
        if isinstance(self.data, dict):

            # TODO: mtime should be the mtime for all files having the
            # same base. E.g. the mtime of foo.jpg should be the sum of the
            # mtimeof foo.jpg and foo.jpg.xml or for foo.mp3 the mtime should
            # be the sum of foo.mp3 and foo.jpg.
            
            if os.stat(self.data['path'])[stat.ST_MTIME] == self.data['mtime']:
                return False
            fname = self.data['name']
            update = True
        else:
            fname = self.data
            update = False

        if self.parent:
            if not self.parent.isdir():
                return False
            dirname = self.parent['path']
            path = dirname + '/' + fname
            parent = self.parent.__id__()
        else:
            dirname = ''
            path = '/'
            parent = None
            
        attributes = { 'mtime': os.stat(path)[stat.ST_MTIME] }
        metadata = kaa.metadata.parse(path)
        type = ''
        if metadata and metadata['media'] and \
               self.db._object_types.has_key(metadata['media']):

            type = metadata['media']
        elif os.path.isdir(path):
            type = 'dir'
        else:
            type = 'file'

        type_list = self.db._object_types[type]
        for key in type_list[1].keys():
            if metadata and metadata.has_key(key) and metadata[key] != None:
                attributes[key] = metadata[key]

        # TODO: do some more stuff here:
        # - check metadata for thumbnail or cover (audio) and use kaa.thumb to store it
        # - schedule thumbnail genereation with kaa.thumb
        # - search for covers based on the file

        if update:
            id = self.data['id']
            self.db.update_object((type, id), **attributes)
            self.data.update(attributes)
        else:
            self.data = self.db.add_object((type, fname), parent=parent, **attributes)
            self.data['path'] = path
        return True
    

    def _update(self):

        # TODO: This function should be called automaticly when __setitem__
        # changed something and should run in the background

        if not self.__changes:
            return False
        self.db.update_object(self.__id__(), **self.__changes)
        self.__changes = {}
        return True
    
        
    def __str__(self):
        if isinstance(self.data, str):
            return 'new file %s' % self.data
        return self.data['name']


    def __id__(self):
        return (self.data['type'], self.data["id"])

    
    def __getitem__(self, key):
        if self.data.has_key(key):
            return self.data[key]
        if self.data.has_key('tmp:' + key):
            return self.data['tmp:' + key]

        # TODO: maybe get cover from parent (e.g. cover in a dir)
        # Or should that be stored in each item
        
        return None


    def __setitem__(self, key, value):
        self.data[key] = value
        if not key.startswith('tmp:'):
            self.__changes[key] = value


    def keys(self):
        return self.data.keys()


    def items(self):
        return self.data.items()


    def has_key(self, key):
        return self.data.has_key(key)

        
    def isdir(self):
        if isinstance(self.data, (str, unicode)):
            return os.path.isdir(self.parent['path'] + '/' + self.data)
        return self.data['type'] == 'dir'

    
    def list(self):
        self._parse()

        if self.data['type'] != 'dir':
            return self.db.query_normalized(parent = self.__id__())
            
        dirname = os.path.normpath(self.data['path'])
        files = self.db.query_normalized(parent = ("dir", self.data["id"]))
        fs_listing = os.listdir(dirname)

        # TODO: add OVERLAY_DIR support
        # Ignore . files
        
        ret = Listing()
        for f in files[:]:
            if f['name'] in fs_listing:
                # file still there
                fs_listing.remove(f['name'])
                ret.append(Item(f, self, self.db))
            else:
                # file deleted
                files.remove(f)
                # FIXME: remove from database

        for f in fs_listing:
            # new files
            ret.append(Item(f, self, self.db))
            
        return ret

            
class MediaDB(Database):

    # TODO: rename MediaDB to VFS
    
    def __init__(self, dbdir):
        if not os.path.exists(dbdir):
            os.makedirs(dbdir)
        elif not os.path.isdir(dbdir):
            raise AttributeError('%s must be a directory')
        
        Database.__init__(self, dbdir + '/db')

        self.register_object_type_attrs("file", ())

        self.register_object_type_attrs("video", (
            ("title", unicode, ATTR_KEYWORDS),
            ("width", int, ATTR_SIMPLE),
            ("height", int, ATTR_SIMPLE),
            ("length", int, ATTR_SIMPLE)))

        self.register_object_type_attrs("audio", (
            ("title", unicode, ATTR_KEYWORDS),
            ("artist", unicode, ATTR_KEYWORDS | ATTR_INDEXED),
            ("album", unicode, ATTR_KEYWORDS),
            ("genre", unicode, ATTR_INDEXED),
            ("samplerate", int, ATTR_SIMPLE),
            ("length", int, ATTR_SIMPLE),
            ("bitrate", int, ATTR_SIMPLE),
            ("trackno", int, ATTR_SIMPLE)))
        
        self.register_object_type_attrs("image", (
            ("width", int, ATTR_SEARCHABLE),
            ("height", int, ATTR_SEARCHABLE),
            ("date", int, ATTR_SEARCHABLE)))

        # TODO: add more known types
        
        root = self.query_normalized(type="dir", name="/")
        if not root:
            root = self.add_object(("dir", "/"))
            # FIXME: get current data from database
            root = self.query_normalized(type='dir', name='/')[0]
        else:
            root = root[0]
        root['path'] = '/'
        self._dir_cache = { '/': Item(root, None, self) }


    def __get_dir(self, dirname):
        if dirname in self._dir_cache:
            return self._dir_cache[dirname]
        pdir = self.__get_dir(os.path.dirname(dirname))
        parent = ("dir", pdir["id"])

        # TODO: handle dirs on romdrives which down have '/'
        # as basic parent
        
        name = os.path.basename(dirname)
        current = self.query_normalized(type="dir", name=name, parent=parent)
        if not current:
            current = self.add_object(("dir", name), parent=parent)
        else:
            current = current[0]
        current['path'] = dirname
        current = Item(current, pdir, self)
        self._dir_cache[dirname] = current
        return current


    def listdir(self, dirname):
        """
        List directory.
        """
        return self.__get_dir(os.path.normpath(os.path.abspath(dirname))).list()


    def file(self, filename):
        """
        Return item for the given file.
        """
        dirname = os.path.dirname(filename)
        basename = os.path.basename(filename)
        dir = self.__get_dir(os.path.normpath(os.path.abspath(dirname)))
        current = self.query_normalized(name=basename, parent=dir.__id__())
        if not current:
            return Item(basename, dir, self)
        return Item(current[0], dir, self)
    

    def do_query(self, **args):
        l = Listing()
        for row in self.query_normalized(**args):
            l.append(Item(row, None, self))
        return l
