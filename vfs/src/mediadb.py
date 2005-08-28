import os
import stat

import kaa.metadata

from db import *

class Listing(object):
    def __init__(self):
        self.items = []

    def __str__(self):
        ret = 'Listing\n'
        for i in self.items:
            ret += '  %s\n' % i
        return ret

    def update(self):
        for i in self.items:
            i._parse()
        

class Item(object):
    def __init__(self, data, dir, db):
        self.data = data
        self.dir = dir
        self.db = db
        if isinstance(self.data, dict) and not self.data.has_key('path'):
            self.data['path'] = self.dir['path'] + '/' + self.data['name']

    def _parse(self):
        if isinstance(self.data, dict):
            if os.stat(self.data['path'])[stat.ST_MTIME] == self.data['mtime']:
                return False
            fname = self.data['name']
            update = True
        else:
            fname = self.data
            update = False

        if self.dir:
            dirname = self.dir['path']
            path = dirname + '/' + fname
            parent = ("dir", self.dir["id"])

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
        else:
            id = self.db.add_object((type, fname), parent=parent, **attributes)['id']
            
        # FIXME: get current data from database
        self.data = self.db.query_normalized(type=type, id=id)[0]
        self.data['path'] = path
        return True
    

    def __str__(self):
        if isinstance(self.data, (str, unicode)):
            return 'new file %s' % self.data
        return self.data['name']


    def __getitem__(self, key):
        return self.data[key]

    
class Directory(Item):
    def list(self):
        self._parse()

        dirname = os.path.normpath(self.data['path'])
        files = self.db.query_normalized(parent = ("dir", self.data["id"]))
        fs_listing = os.listdir(dirname)

        ret = Listing()
        for f in files[:]:
            if f['name'] in fs_listing:
                # file still there
                fs_listing.remove(f['name'])
                ret.items.append(Item(f, self, self.db))
            else:
                # file deleted
                files.remove(f)
                # FIXME: remove from database

        for f in fs_listing:
            # new files
            if os.path.isdir(dirname + '/' + f):
                ret.items.append(Directory(f, self, self.db))
            else:
                ret.items.append(Item(f, self, self.db))
            
        return ret


    def __str__(self):
        if isinstance(self.data, (str, unicode)):
            return 'new dir %s' % self.data
        return 'dir ' + self.data['name']

            
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
        self.dir = { '/': Directory(root, None, self) }


    def __get_dir(self, dirname):
        if dirname in self.dir:
            return self.dir[dirname]
        pdir = self.__get_dir(os.path.dirname(dirname))
        parent = ("dir", pdir["id"])
        
        name = os.path.basename(dirname)
        current = self.query_normalized(type="dir", name=name, parent=parent)
        if not current:
            current = self.add_object(("dir", name), parent=parent)
            # FIXME: get current data from database
            current = self.query_normalized(type='dir', name=name, parent=parent)
        current = current[0]
        current['path'] = dirname
        current = Directory(current, pdir, self)
        self.dir[dirname] = current
        return current


    def listdir(self, dirname):
        """
        List directory.
        """
        return self.__get_dir(os.path.normpath(os.path.abspath(dirname))).list()
