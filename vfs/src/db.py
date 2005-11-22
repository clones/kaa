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
import item
import util

# get logging object
log = logging.getLogger('vfs')

MAX_BUFFER_CHANGES = 20

class Mountpoint(object):
    """
    Internal class for mountpoints. More a list of attributes important
    for each mountpoint.
    """
    def __init__(self, device, directory):
        self.device = device
        self.directory = directory
        self.name = None
        self._id = None


    def set_name(self, name):
        """
        Set name of the mountpoint (== load new media)
        """
        if name == self.name:
            return False
        self.name = name
        self._id = None
        return True


    def id(self, db, read_only):
        """
        Get the id of the mountpoint. This functions needs the database
        and _must_ be called from the same thread as the db itself.
        """
        if self._id:
            # id already known
            return self._id
        if self.name == None:
            # no disc
            return self._id
        media = db.query(type="media", name=self.name)
        if not media and read_only:
            # not known but we are not allowed to write the db
            return None
        if media:
            # known, set internal id and return it
            self._id = ('media', media[0]['id'])
        else:
            # create media entry and root filesystem
            log.info('create root filesystem for %s' % self.name)
            self._id = ('media', db.add_object("media", name=self.name)['id'])
        if not db.query(type='dir', name='', parent=self._id) and not read_only:
            db.add_object("dir", name="", parent=self._id)
        db.commit()
        return self._id

        
    def __str__(self):
        """
        Convert object to string (usefull for debugging)
        """
        return '<vfs.Mountpoint for %s>' % self.directory


class Database(object):
    """
    A kaa.db based database.
    """

    def __init__(self, dbdir):
        """
        Init function
        """
        # internal db dir, it contains the real db and the
        # overlay dir for the vfs
        self.dbdir = dbdir

        # flag if the db should be read only
        self.read_only = False

        # handle changes in a list and add them to the database
        # on commit.
        self.changes = []

        # internal list of mountpoints
        self._mountpoints = []

        # create db
        if not os.path.isdir(self.dbdir):
            os.makedirs(self.dbdir)
        self._db = db.Database(self.dbdir + '/db')

        # register basic types
        self._db.register_object_type_attrs("dir",
            name = (str, ATTR_KEYWORDS_FILENAME),
            mtime = (int, ATTR_SIMPLE))

        self._db.register_object_type_attrs("file",
            name = (str, ATTR_KEYWORDS_FILENAME),
            mtime = (int, ATTR_SIMPLE))

        self._db.register_object_type_attrs("media",
            name = (str, ATTR_KEYWORDS),
            content = (str, ATTR_SIMPLE))

        # commit
        self._db.commit()


    def add_mountpoint(self, device, directory):
        """
        Add a mountpoint to the system.
        """
        for mountpoint in self._mountpoints:
            if mountpoint.directory == directory:
                return False
        mountpoint = Mountpoint(device, directory)
        self._mountpoints.append(mountpoint)
        self._mountpoints.sort(lambda x,y: -cmp(x.directory, y.directory))
        return True


    def get_mountpoints(self, return_objects=False):
        """
        Return current list of mountpoints
        """
        if return_objects:
            return self._mountpoints
        return [ (m.device, m.directory, m.name) for m in self._mountpoints ]


    def set_mountpoint(self, directory, name):
        """
        Set name of the mountpoint (load a media)
        """
        for mountpoint in self._mountpoints:
            if mountpoint.directory == directory:
                return mountpoint.set_name(name)
        else:
            raise AttributeError('unknown mountpoint')

        
    def __getattr__(self, attr):
        """
        Interface to the db.
        """
        if attr == 'object_types':
            # return the attribute _object_types from the db
            return self._db._object_types
        raise AttributeError(attr)


    def _get_dir(self, dirname, media, root):
        """
        Get database entry for the given directory. Called recursive to
        find the current entry. Do not cache results, they could change.
        """
        if not media:
            # Unknown media and looks like we are read only.
            # Return None, if the media is not known, the dir also won't
            log.info('no media set')
            return None
        if dirname == root:
            # we know that '/' is in the db
            current = self._db.query(type="dir", name='', parent=media)[0]
            return item.create(current, root)
        parent = self._get_dir(os.path.dirname(dirname), media, root)
        if not parent:
            return None

        # TODO: handle dirs on romdrives which don't have '/'
        # as basic parent

        name = os.path.basename(dirname)
        current = self._db.query(type="dir", name=name, parent=parent.dbid)
        if not current and self.read_only:
            log.info('not in db and read only db')
            return None
        if not current:
            current = self._db.add_object("dir", name=name, parent=parent.dbid)
            self._db.commit()
        else:
            current = current[0]
        return item.create(current, parent)


    def commit(self):
        """
        Commit changes to the database. All changes in the internal list
        are done first.
        """
        t1 = time.time()
        changes = self.changes
        for c in self.changes:
            # It could be possible that an item is added twice. But this is no
            # problem because the duplicate will be removed at the
            # next query. It can also happen that a dir is added because of
            # _getdir and because of the parser. We can't avoid that but the
            # db should clean itself up.
            c[0](*c[1], **c[2])
        self._db.commit()
        self.changes = []
        log.info('db.commit took %s seconds' % (time.time() - t1))


    def _delete(self, entry):
        """
        Delete item with the given id from the db and all items with that
        items as parent (and so on). To avoid internal problems, make sure
        commit is called just after this function is called.
        """
        log.debug('DELETE %s' % entry)
        for child in self._db.query(parent = (entry['type'], entry['id'])):
            self._delete(child)
        self.delete_object((entry['type'], entry['id']))


    def _query_dirname(self, *args, **kwargs):
        """
        A query to get all files in a directory. Special keyword 'dirname' in
        the query is used for that.
        """
        dirname = kwargs['dirname']
        del kwargs['dirname']
        # find correct mountpoint
        for m in self._mountpoints:
            if dirname.startswith(m.directory):
                break
        parent = self._get_dir(dirname, m.id(self._db, self.read_only), m.directory)
        if parent:
            files = self._db.query(parent = ("dir", parent["id"]))
        else:
            files = []
            parent = dirname + '/'

        fs_listing = util.listdir(dirname, self.dbdir)
        need_commit = False

        items = []
        for f in files[:]:
            # FIXME: for some very very strange reason this can take about
            # 2 seconds for 700 files. I'm not sure why. Some files are
            # processed and then python changes the thread to a new one. Only
            # the main thread is running right now and this thread is polling
            # using step() and step uses a select which should release the
            # interpreter lock. But this does not happen, the main thread is
            # doing _blocking_ selects (nothing to read) for up to 2 seconds
            # and this thread can't do anything. Maybe using a thread for db
            # access is not such a good thing afterall.
            # Note: for some more stranger reason the problem starts the same
            # moment when the client is sending the query to the server to do
            # the same query.
            #
            # Test it with a large dir and by activating this following
            # debug:
            # print f['name']
            if f['name'] in fs_listing:
                # file still there
                fs_listing.remove(f['name'])
                items.append(item.create(f, parent))
            else:
                # file deleted
                files.remove(f)
                if not self.read_only:
                    # delete from database by adding it to the internal changes
                    # list. It will be deleted right before the next commit.
                    self.changes.append((self._delete, [f], {}))
                    need_commit = True

        for f in fs_listing:
            # new files
            items.append(item.create(f, parent))

        if need_commit:
            # need commit because some items were deleted from the db
            self._commit()

        # sort result
        items.sort(lambda x,y: cmp(x.url, y.url))
        return items


    def _query_files(self, *args, **kwargs):
        """
        A query to get a list of files. Special keyword 'filenames' (list) in
        the query is used for that.
        """
        files = kwargs['files']
        del kwargs['files']
        items = []
        for f in files:
            dirname = os.path.dirname(f)
            basename = os.path.basename(f)
            # TODO: cache parents here
            # find correct mountpoint
            for m in self._mountpoints:
                if dirname.startswith(m.directory):
                    break
            parent = self._get_dir(dirname, m.id(self._db, self.read_only), m.directory)
            if parent:
                dbentry = self._db.query(parent = parent.dbid, name=basename)
                if not dbentry:
                    dbentry = basename
                else:
                    dbentry = dbentry[0]
            else:
                parent = dirname
                dbentry = basename
            items.append(item.create(dbentry, parent))
        return items


    def _query_attr(self, *args, **kwargs):
        """
        A query to get a list of possible values of one attribute. Special
        keyword 'attr' the query is used for that. This query will not return
        a list of items.
        """
        kwargs['distinct'] = True
        kwargs['attrs'] = [ kwargs['attr'] ]
        del kwargs['attr']
        return [ x[1] for x in self._db.query_raw(**kwargs)[1] if x[1] ]


    def _query_device(self, *args, **kwargs):
        """
        A query to monitor a media (mountpoint). Special keyword 'media' in
        the query is used for that.
        """
        device = kwargs['device']
        del kwargs['device']
        for m in self._mountpoints:
            if m.device == device:
                id = m.id(self._db, self.read_only)
                if not id:
                    # TODO: maybe always return one item with the result
                    return []
                media = self._db.query(type='media', id=id[1])
                if media[0]['content'] == 'dir':
                    # a simple data dir
                    return [ self._get_dir(m.directory, id, m.directory) ]
                # TODO: support other media
                return [ ]
        # TODO: raise an exception
        return []

    
    def query(self, *args, **kwargs):
        """
        Internal query function inside the thread. This function will use the
        corrent internal query function based on special keywords.
        """
        if 'dirname' in kwargs:
            return self._query_dirname(*args, **kwargs)
        if 'files' in kwargs:
            return self._query_files(*args, **kwargs)
        if 'attr' in kwargs:
            return self._query_attr(*args, **kwargs)
        if 'device' in kwargs:
            return self._query_device(*args, **kwargs)
        return self._db.query(*args, **kwargs)


    def add_object(self, *args, **kwargs):
        """
        Add an object to the db. If the keyword 'vfs_immediately' is set, the
        object will be added now and the db will be locked until the next commit.
        To avoid locking, do not se the keyword, but this means that a requery on
        the object won't find it before the next commit.
        """
        if 'vfs_immediately' in kwargs:
            del kwargs['vfs_immediately']
            return self._db.add_object(*args, **kwargs)
        self.changes.append((self._db.add_object, args, kwargs))
        if len(self.changes) > MAX_BUFFER_CHANGES:
            self.commit()


    def update_object(self, *args, **kwargs):
        """
        Update an object to the db. If the keyword 'vfs_immediately' is set, the
        object will be updated now and the db will be locked until the next commit.
        To avoid locking, do not se the keyword, but this means that a requery on
        the object will return the old values.
        """
        if 'vfs_immediately' in kwargs:
            del kwargs['vfs_immediately']
            return self._db.update_object(*args, **kwargs)
        self.changes.append((self._db.update_object, args, kwargs))
        if len(self.changes) > MAX_BUFFER_CHANGES:
            self.commit()


    def register_object_type_attrs(self, *args, **kwargs):
        """
        Register a new object with attributes. Special keywords like name and
        mtime are added by default.
        """
        kwargs['name'] = (str, ATTR_KEYWORDS_FILENAME)
        kwargs['mtime'] = (int, ATTR_SIMPLE)
        return self._db.register_object_type_attrs(*args, **kwargs)
