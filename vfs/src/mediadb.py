import os
import stat

import kaa.metadata

from kaa.base.db import *

# TODO: put all the sql stuff in a thread and have a client server
# model between main and thread. After that, move the thread into an
# extra process. Later a mixture may be a good idea. A process to
# write (to only have one writer) and a thread for reading (process
# intern may be faster).

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

            # TODO: handle parents not based on file:

            if self.parent['url'] == 'file:/':
                self.data['url'] = 'file:/' + self.data['name']
            else:
                self.data['url'] = self.parent['url'] + '/' + self.data['name']
        self.__changes = {}

        
    def _parse(self):
        if isinstance(self.data, dict):

            if not self.data['url'].startswith('file:'):
                # no need to update other information than file urls
                return False

            fname = self.data['name']
            update = True

        else:
            fname = self.data
            update = False

        if self.parent:
            if not self.parent.isdir():
                return False
            dirname = self.parent['url'][5:]
            path = dirname + '/' + fname
            parent = self.parent.__id__()
        else:
            dirname = ''
            path = '/'
            parent = None
            
        mtime = 0
        if self.parent and not self.isdir():

            # mtime is the the mtime for all files having the same
            # base. E.g. the mtime of foo.jpg is the sum of the
            # mtimeof foo.jpg and foo.jpg.xml or for foo.mp3 the
            # mtime is the sum of foo.mp3 and foo.jpg.
            
            base = os.path.splitext(fname)[0]
            
            # TODO: add overlay support
            
            # TODO: Make this much faster. We should cache the listdir
            # and the stat results somewhere, maybe already split by ext
            # But since this is done in background, this is not so
            # important right now.
            
            files = map(lambda x: dirname + '/' + x, os.listdir(dirname))
            for f in filter(lambda x: x.startswith(base), files):
                mtime += os.stat(f)[stat.ST_MTIME]
        else:
            mtime = os.stat(path)[stat.ST_MTIME]

        if isinstance(self.data, dict) and mtime == self.data['mtime']:
            # no need to update
            return False
            
        attributes = { 'mtime': mtime }
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
        # - search for covers based on the file (should be done by kaa.metadata)

        if update:
            id = self.data['id']
            self.db.update_object((type, id), **attributes)
            self.data.update(attributes)
        else:
            self.data = self.db.add_object((type, fname), parent=parent, **attributes)
            self.data['url'] = 'file:' + path
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
            return os.path.isdir(self.parent['url'][5:] + '/' + self.data)
        return self.data['type'] == 'dir'

    
    def list(self):
        self._parse()

        if self.data['type'] != 'dir':
            return self.db.query_normalized(parent = self.__id__())
            
        dirname = os.path.normpath(self.data['url'][5:])
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
        root['url'] = 'file:/'
        root = Item(root, None, self)
        self._dir_cache = { '/': root }
        self._parent_cache = { root.__id__(): root }
        

    def __get_dir(self, dirname):
        if dirname in self._dir_cache:
            return self._dir_cache[dirname]
        pdir = self.__get_dir(os.path.dirname(dirname))
        parent = ("dir", pdir["id"])

        # TODO: handle dirs on romdrives which don't have '/'
        # as basic parent
        
        name = os.path.basename(dirname)
        current = self.query_normalized(type="dir", name=name, parent=parent)
        if not current:
            current = self.add_object(("dir", name), parent=parent)
        else:
            current = current[0]
        current['url'] = 'file:' + dirname
        current = Item(current, pdir, self)
        self._dir_cache[dirname] = current
        self._parent_cache[current.__id__()] = current
        return current


    def __get_parent(self, id):
        if id in self._parent_cache:
            return self._parent_cache[id]
        object = self.query_normalized(type=id[0], id=id[1])[0]

        # TODO: handle objects without parents (e.g. rom drives)

        parent = self.__get_parent(object['parent'])
        object = Item(object, parent, self)
        self._parent_cache[id] = object
        return object
        

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
        result = self.query_normalized(**args)

        if 'attrs' in args:
            # The user specified that only some args should be returned.
            # In this case we can not create a valid Item for a listing and
            # the data is returned as it is.
            if len(args['attrs']) == 1:
                # Only one result, reduce the list of dicts to a list. Also
                # remove the 'None' result
                attr = args['attrs'][0]
                result = [ x[attr] for x in result if x != None ]
            return Listing(result)

        l = Listing()
        result.sort(lambda x,y: cmp(x['parent'], y['parent']))
        last_parent_id = None
        for row in result:
            parent = row['parent']
            if last_parent_id != parent:
                # find correct parent
                last_parent = self.__get_parent(parent)
                last_parent_id = parent
            l.append(Item(row, last_parent, self))
        return l
