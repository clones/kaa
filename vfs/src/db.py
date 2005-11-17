# -*- coding: iso-8859-1 -*-
# -----------------------------------------------------------------------------
# db.py - Database for the VFS
# -----------------------------------------------------------------------------
# $Id: device.py 799 2005-09-16 14:27:36Z rshortt $
#
# TODO: handle all the FIXME and TODO comments inside this file and
#       add docs for functions, variables and how to use this file
#
# -----------------------------------------------------------------------------
# kaa-vfs - A virtual filesystem with metadata
# Copyright (C) 2005 Dirk Meyer
#
# First Edition: Dirk Meyer <dmeyer@tzi.de>
# Maintainer:    Dirk Meyer <dmeyer@tzi.de>
#
# Please see the file doc/CREDITS for a complete list of authors.
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful, but
# WITHOUT ANY WARRANTY; without even the implied warranty of MER-
# CHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the GNU General
# Public License for more details.
#
# You should have received a copy of the GNU General Public License along
# with this program; if not, write to the Free Software Foundation, Inc.,
# 59 Temple Place, Suite 330, Boston, MA 02111-1307 USA
#
# -----------------------------------------------------------------------------

# python imports
import os
import threading
import logging
import time

# kaa imports
import kaa.notifier
from kaa.base import db
from kaa.base.db import *

# kaa.vfs imports
from item import Item
import util

# get logging object
log = logging.getLogger('vfs')

class Database(threading.Thread):
    """
    A kaa.db based database in a thread.
    """

    class Query(object):
        """
        A query for the database with async callbacks to handle
        the results from the thread in the main loop.
        """
        def __init__(self, db, function):
            self.db = db
            self.function = function
            self.value = None
            self.valid = False
            self.exception = False
            self.callbacks = []

        def __call__(self, *args, **kwargs):
            self.db.condition.acquire()
            self.db.jobs.append((self, self.function, args, kwargs))
            self.db.condition.notify()
            self.db.condition.release()
            return self

        def connect(self, function, *args, **kwargs):
            if self.valid:
                return function(*args, **kwargs)
            cb = kaa.notifier.MainThreadCallback(function, *args, **kwargs)
            self.callbacks.append(cb)

        def set_value(self, value, exception=False):
            self.value = value
            self.exception = exception
            self.valid = True
            for callback in self.callbacks:
                callback()

        def get(self):
            while not self.valid:
                kaa.notifier.step()
            return self.value


    def __init__(self, dbdir):
        """
        Init function for the threaded database.
        """
        # threading setup
        threading.Thread.__init__(self)
        self.setDaemon(True)
        self.stopped = False

        # internal db dir, it contains the real db and the
        # overlay dir for the vfs
        self.dbdir = dbdir

        # list of jobs for the thread and the condition to
        # change that list
        self.jobs = [ None ]
        self.condition = threading.Condition()

        # flag if the db should be read only
        self.read_only = False

        # handle changes in a list and add them to the database
        # on commit. This needs a lock because objects can be added
        # from the main loop and commit is called inside a thread
        self.changes_lock = threading.Lock()
        self.changes = []

        # start thread
        self.start()
        # wait for complete database setup
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


    def _query_dirname(self, *args, **kwargs):
        dirname = kwargs['dirname']
        del kwargs['dirname']
        parent = self.get_dir(dirname)
        if parent:
            files = self._db.query(parent = ("dir", parent["id"]))
        else:
            files = []
            parent = dirname + '/'

        fs_listing = util.listdir(dirname, self.dbdir)

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

        # sort result
        items.sort(lambda x,y: cmp(x.url, y.url))
        return items

    def _query_attr(self, *args, **kwargs):
        kwargs['distinct'] = True
        kwargs['attrs'] = [ kwargs['attr'] ]
        del kwargs['attr']
        return [ x[1] for x in self._db.query_raw(**kwargs)[1] if x[1] ]

    def _query(self, *args, **kwargs):
        if 'dirname' in kwargs:
            return self._query_dirname(*args, **kwargs)
        if 'attr' in kwargs:
            return self._query_attr(*args, **kwargs)
        return self._db.query(*args, **kwargs)


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
                # free memory
                callback = function = r = None
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
                callback.set_value(r)
                kaa.notifier.wakeup()
            except Exception, e:
                log.exception("database error")
                callback.set_value(e, True)
                kaa.notifier.wakeup()
