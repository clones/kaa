import os
import threading
import logging
import time

import kaa
import kaa.notifier
import kaa.notifier.thread
from kaa.base import db
from kaa.base.db import *

from item import Item

# get logging object
log = logging.getLogger('vfs')

class DatabaseError:
    def __init__(self, msg):
        self.msg = msg

    def __str__(self):
        return self.msg
    
class Database(threading.Thread):

    class Query(object):
        def __init__(self, db, function):
            self.db = db
            self.function = function
            self.value = None
            self.valid = False
            self.exception = False
            
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
        self.read_only = False

        self.changes_lock = threading.Lock()
        self.changes = []

        self.start()

        self.wait()

        
    def __getattr__(self, attr):
        if attr == '_object_types':
            return self._db._object_types
        if attr in ('commit', 'query'):
            return Database.Query(self, getattr(self, '_' + attr))
        return Database.Query(self, getattr(self._db, attr))


    def get_dir(self, dirname):
        if dirname in self._dir_cache:
            return self._dir_cache[dirname]
        pdir = self.get_dir(os.path.dirname(dirname))
        if not pdir:
            return None
        parent = ("dir", pdir["id"])

        # TODO: handle dirs on romdrives which don't have '/'
        # as basic parent
        
        name = os.path.basename(dirname)
        current = self._db.query(type="dir", name=name, parent=parent)
        if not current and self.read_only:
            return
        if not current:
            current = self._db.add_object("dir", name=name, parent=parent)
            self._db.commit()
        else:
            current = current[0]
        current['url'] = 'file:' + dirname
        current = Item(current, pdir, self._db)
        self._dir_cache[dirname] = current
        self._parent_cache[current.dbid] = current
        return current


    def _commit(self):
        self.changes_lock.acquire()
        changes = self.changes
        self.changes = []
        self.changes_lock.release()
        for c in changes:
            c[0](*c[1], **c[2])
        self._db.commit()

        
    def _query(self, *args, **kwargs):
        if not 'dirname' in kwargs:
            return self._db.query(*args, **kwargs)
        dirname = os.path.normpath(kwargs['dirname'])
        del kwargs['dirname']

        parent = self.get_dir(dirname)
        if parent:
            files = self._db.query(parent = ("dir", parent["id"]))
        else:
            print 'parent not found'
            files = []
            parent = dirname + '/'
            
        fs_listing = os.listdir(dirname)

        # TODO: add OVERLAY_DIR support
        # Ignore . files

        items = []
        for f in files[:]:
            if f['name'] in fs_listing:
                # file still there
                fs_listing.remove(f['name'])
                items.append(Item(f, parent, self))
            else:
                # file deleted
                files.remove(f)
                # FIXME: remove from database

        for f in fs_listing:
            # new files
            items.append(Item(f, parent, self))
            
        return items


    def add_object(self, *args, **kwargs):
        if 'vfs_immediately' in kwargs:
            del kwargs['vfs_immediately']
            return Database.Query(self, self._db.add_object)(*args, **kwargs)
        self.changes_lock.acquire()
        self.changes.append((self._db.add_object, args, kwargs))
        self.changes_lock.release()


    def update_object(self, *args, **kwargs):
        if 'vfs_immediately' in kwargs:
            del kwargs['vfs_immediately']
            return Database.Query(self, self._db.update_object)(*args, **kwargs)
        self.changes_lock.acquire()
        self.changes.append((self._db.update_object, args, kwargs))
        self.changes_lock.release()


    def register_object_type_attrs(self, *args, **kwargs):
        kwargs['name'] = (str, ATTR_KEYWORDS_FILENAME)
        kwargs['mtime'] = (int, ATTR_SIMPLE)
        return Database.Query(self, self._db.register_object_type_attrs)(*args, **kwargs)
        

    def wait(self):
        if not self.jobs:
            return
        Database.Query(self, None)().get()
        

    def run(self):
        if not os.path.isdir(self.dbdir):
            os.makedirs(self.dbdir)
        self._db = db.Database(self.dbdir + '/db')

        self._db.register_object_type_attrs("dir",
            name = (str, ATTR_KEYWORDS_FILENAME),
            mtime = (int, ATTR_SIMPLE))

        self._db.register_object_type_attrs("file",
            name = (str, ATTR_KEYWORDS_FILENAME),
            mtime = (int, ATTR_SIMPLE))

        root = self._db.query(type="dir", name="/")
        if not root:
            root = self._db.add_object("dir", name="/")
        else:
            root = root[0]
        root['url'] = 'file:/'
        root = Item(root, None, self._db)
        self._dir_cache = { '/': root }
        self._parent_cache = { root.dbid: root }

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
                    t1 = time.time()
                    r = function(*args, **kwargs)
                    t2 = time.time()
                callback.value = r
                callback.valid = True
                kaa.notifier.wakeup()
            except DatabaseError, e:
                callback.value = e
                callback.valid = True
                callback.exception = True
                kaa.notifier.wakeup()
            except:
                log.exception("oops")
                callback.valid = True
                kaa.notifier.wakeup()
