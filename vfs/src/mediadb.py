import os
import stat

import kaa.metadata

from db import *

class Listing(list):
        
    def update(self):
        for i in self:
            i._parse()


    def __str__(self):
        ret = 'Listing\n'
        for i in self:
            ret += '  %s\n' % i
        return ret


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

        if update:
            id = self.data['id']
            self.db.update_object((type, id), **attributes)
            self.data.update(attributes)
        else:
            self.data = self.db.add_object((type, fname), parent=parent, **attributes)
            self.data['path'] = path
        return True
    

    def _update(self):
        if not self.__changes:
            return False
        self.db.update_object(self.__id__(), **self.__changes)
        self.__changes = {}
        return True
    
        
    def __str__(self):
        if isinstance(self.data, (str, unicode)):
            return 'new file %s' % self.data
        return self.data['name']


    def __id__(self):
        return (self.data['type'], self.data["id"])

    
    def __getitem__(self, key):
        if self.data.has_key(key):
            return self.data[key]
        if self.data.has_key('tmp:' + key):
            return self.data['tmp:' + key]
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

    def __init__(self, dbfile = None):
        Database.__init__(self, dbfile)
        self.register_object_type_attrs("file", ())

        self.register_object_type_attrs("video", (
            ("title", str, ATTR_KEYWORDS),
            ("width", int, ATTR_SIMPLE),
            ("height", int, ATTR_SIMPLE),
            ("length", int, ATTR_SIMPLE)))

        self.register_object_type_attrs("audio", (
            ("title", str, ATTR_KEYWORDS),
            ("artist", str, ATTR_KEYWORDS | ATTR_INDEXED),
            ("album", str, ATTR_KEYWORDS),
            ("genre", str, ATTR_INDEXED),
            ("samplerate", int, ATTR_SIMPLE),
            ("length", int, ATTR_SIMPLE),
            ("bitrate", int, ATTR_SIMPLE),
            ("trackno", int, ATTR_SIMPLE)))
        
        self.register_object_type_attrs("image", (
            ("width", int, ATTR_SEARCHABLE),
            ("height", int, ATTR_SEARCHABLE),
            ("date", int, ATTR_SEARCHABLE)))
        
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
        
        name = os.path.basename(dirname)
        current = self.query_normalized(type="dir", name=name, parent=parent)
        if not current:
            current = self.add_object(("dir", name), parent=parent)
            print current
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
    
