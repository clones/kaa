import os

import kaa.metadata

from db import *

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
        else:
            root = root[0]
        self.dir = { '/': root }


    def __get_dir(self, dirname):
        if dirname in self.dir:
            return self.dir[dirname]
        parent = self.__get_dir(os.path.dirname(dirname))
        parent = ("dir", parent["id"])
        
        name = os.path.basename(dirname)
        current = self.query_normalized(type="dir", name=name, parent=parent)
        if not current:
            current = self.add_object(("dir", name), parent=parent)
        else:
            current = current[0]
        self.dir[dirname] = current
        return current


    def scan_dir(self, dirname):
        dirname = os.path.normpath(os.path.abspath(dirname))
        dir = self.__get_dir(dirname)
        files = self.query_normalized(parent = ("dir", dir["id"]))
        listing = os.listdir(dirname)
        for f in files:
            if f['name'] in listing:
                # file still there
                listing.remove(f['name'])
            else:
                # file deleted
                print 'deleted'

        # new files
        for fname in listing:
            metadata = kaa.metadata.parse(dirname + '/' + fname)
            if metadata and metadata['media'] and \
                   self._object_types.has_key(metadata['media']):
                type_list = self._object_types[metadata['media']]
                attributes = {}
                for key in type_list[1].keys():
                    if metadata.has_key(key) and metadata[key] != None:
                        attributes[key] = metadata[key]
                self.add_object((metadata['media'], fname), parent=("dir", dir["id"]),
                              **attributes)
            elif os.path.isdir('/home/dmeyer/mp3/' + fname):
                self.add_object(("dir", fname), parent=("dir", dir["id"]))
            else:
                self.add_object(("file", fname), parent=("dir", dir["id"]))


    def listdir(self, dirname):
        dirname = os.path.normpath(os.path.abspath(dirname))
        dir = self.__get_dir(dirname)
        files = self.query_normalized(parent = ("dir", dir["id"]))
        return dir, files
