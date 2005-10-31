import os
import threading
import logging

import kaa
import kaa.notifier
import kaa.notifier.thread
from kaa.base import db
from kaa.base.db import *

from item import Item

# get logging object
log = logging.getLogger('vfs')

class Database(threading.Thread):

    class Query(object):
        def __init__(self, db, function):
            self.db = db
            self.function = function
            self.value = None
            self.valid = False

        def __call__(self, *args, **kwargs):
            self.db.condition.acquire()
            self.db.jobs.append((self, self.function, args, kwargs))
            self.db.condition.notify()
            self.db.condition.release()
            return self

        def get(self):
            while not self.valid:
                kaa.notifier.step()
            return self.value
        
    def __init__(self, dbdir):
        threading.Thread.__init__(self)
        self.setDaemon(True)
        self.condition = threading.Condition()
        self.stopped = False
        self.jobs = [ None ]
        self.dbdir = dbdir
        self.start()
        self.wait()

        
    def __getattr__(self, attr):
        return Database.Query(self, getattr(self._db, attr))

    
    def wait(self):
        if not self.jobs:
            return
        Database.Query(self, None)().get()
        
    def run(self):
        if not os.path.isdir(self.dbdir):
            os.makedirs(self.dbdir)
        self._db = db.Database(self.dbdir + '/db')
        # remove dummy job for startup
        self.jobs = self.jobs[1:]

        while not self.stopped:
            self.condition.acquire()
            while not self.jobs and not self.stopped:
                self.condition.wait()
            if self.stopped:
                self.condition.release()
                continue
            callback, function, args, kwargs = self.jobs[0]
            self.jobs = self.jobs[1:]
            self.condition.release()
            try:
                r = None
                if function:
                    r = function(*args, **kwargs)
                callback.value = r
                callback.valid = True
                kaa.notifier.wakeup()
            except:
                log.exception("oops")
                callback.valid = True
                kaa.notifier.wakeup()


class Server(object):
    def __init__(self, dbdir):
        self._db = Database(dbdir)

        self.register_object_type_attrs("dir",
            name = (str, ATTR_KEYWORDS_FILENAME),
            mtime = (int, ATTR_SIMPLE))

        self.register_object_type_attrs("file",
            name = (str, ATTR_KEYWORDS_FILENAME),
            mtime = (int, ATTR_SIMPLE))

        self.register_object_type_attrs("video",
            name = (str, ATTR_KEYWORDS_FILENAME),
            mtime = (int, ATTR_SIMPLE),
            title = (unicode, ATTR_KEYWORDS),
            width = (int, ATTR_SIMPLE),
            height = (int, ATTR_SIMPLE),
            length = (int, ATTR_SIMPLE))

        self.register_object_type_attrs("audio",
            name = (str, ATTR_KEYWORDS_FILENAME),
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
            name = (str, ATTR_KEYWORDS_FILENAME),
            mtime = (int, ATTR_SIMPLE),
            width = (int, ATTR_SEARCHABLE),
            height = (int, ATTR_SEARCHABLE),
            date = (unicode, ATTR_SEARCHABLE))

        # TODO: add more known types

        root = self._db.query(type="dir", name="/").get()
        if not root:
            root = self._db.add_object("dir", name="/").get()
            print root
            root = self._db.query(type='dir', name='/').get()[0]
            print root
        else:
            root = root[0]
        root['url'] = 'file:/'
        root = Item(root, None, self._db)
        self._dir_cache = { '/': root }
        self._parent_cache = { root.__id__(): root }
        
    def register_object_type_attrs(self, *args, **kwargs):
        return self._db.register_object_type_attrs(*args, **kwargs)


print 'a'
s = Server('xxx')

print 'go'
print 'go2'
kaa.main()
