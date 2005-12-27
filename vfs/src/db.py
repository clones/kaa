# -*- coding: iso-8859-1 -*-
# -----------------------------------------------------------------------------
# db.py - Database for the VFS
# -----------------------------------------------------------------------------
# $Id$
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


    # TODO: make this object visible to the client and add mount and umount
    # functions to it. But we need different kinds of classes for client
    # and server because the client needs to use ipc for the mounting.

    def __init__(self, device, directory, vfsdir, db, read_only):
        self.device = device
        self.directory = directory
        self.name = None
        self.id = None
        self.vfsdir = vfsdir
        self.db = db
        self.read_only = read_only
        self.overlay = ''
        self.url = ''

    def load(self, name):
        """
        Set name of the mountpoint (== load new media)
        """
        if name == self.name:
            return False
        self.name = name
        self.id = None
        self.url = ''
        # get the db id
        if self.name != None:
            media = self.db.query(type="media", name=self.name)
            if media:
                # known, set internal id
                media = media[0]
                self.id = ('media', media['id'])
            elif not self.read_only:
                # create media entry and root filesystem
                log.info('create media entry for %s' % self.name)
                media = self.db.add_object("media", name=self.name, content='file')
                self.id = ('media', media['id'])
            if not self.db.query(type='dir', name='', parent=self.id) and \
                   not self.read_only:
                log.info('create root filesystem for %s' % self.name)
                self.db.add_object("dir", name="", parent=self.id)
            if not self.read_only:
                self.db.commit()
            if media:
                self.url = media['content'] + '//' + self.directory
            if name:
                self.overlay = os.path.join(self.vfsdir, name)
                if not os.path.isdir(self.overlay):
                    os.mkdir(self.overlay)
            else:
                self.overlay = ''
        return True


    def item(self):
        """
        Get the id of the mountpoint. This functions needs the database
        and _must_ be called from the same thread as the db itself.
        Return the root item for the mountpoint.
        """
        if not self.id:
             return None
        media = self.db.query(type='media', id=self.id[1])
        content = media[0]['content']
        if content == 'file':
            # a simple data dir
            current = self.db.query(type="dir", name='', parent=self.id)[0]
            return item.create(current, None, self)
        # a track of something else
        return [ item.create(x, self, self) for x in \
                 self.db.query(type='track_%s' % content, parent=self.id) ]
        # TODO: support other media
        return None

        
    def __str__(self):
        """
        Convert object to string (usefull for debugging)
        """
        return '<vfs.Mountpoint for %s>' % self.directory


    def __del__(self):
        return 'del', self


class Database(object):
    """
    A kaa.db based database.
    """

    def __init__(self, dbdir, read_only):
        """
        Init function
        """
        # internal db dir, it contains the real db and the
        # overlay dir for the vfs
        self.dbdir = dbdir

        # flag if the db should be read only
        self.read_only = read_only

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
            overlay = (bool, ATTR_SIMPLE),
            media = (int, ATTR_SIMPLE),
            mtime = (int, ATTR_SIMPLE))

        self._db.register_object_type_attrs("file",
            name = (str, ATTR_KEYWORDS_FILENAME),
            overlay = (bool, ATTR_SIMPLE),
            media = (int, ATTR_SIMPLE),
            mtime = (int, ATTR_SIMPLE))

        self._db.register_object_type_attrs("media",
            name = (str, ATTR_KEYWORDS),
            title = (unicode, ATTR_KEYWORDS),
            overlay = (bool, ATTR_SIMPLE),
            length = (int, ATTR_SIMPLE),
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
        mountpoint = Mountpoint(device, directory, self.dbdir, self._db, self.read_only)
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
                return mountpoint.load(name)
        else:
            raise AttributeError('unknown mountpoint')

        
    def __getattr__(self, attr):
        """
        Interface to the db.
        """
        if attr == 'object_types':
            # Return the attribute _object_types from the db.
            # TODO: Make this a real variable which only contains the stuff
            # we need here and make sure it is in sync between server and clients
            return self._db._object_types
        raise AttributeError(attr)


    def _get_dir(self, dirname, media):
        """
        Get database entry for the given directory. Called recursive to
        find the current entry. Do not cache results, they could change.
        """
        if not media:
            # Unknown media and looks like we are read only.
            # Return None, if the media is not known, the dir also won't
            # Note: this should never happen
            log.error('no media set, this should never happen')
            return None
        if dirname == media.directory:
            # we know that '/' is in the db
            current = self._db.query(type="dir", name='', parent=media.id)[0]
            return item.create(current, None, media)

        parent = self._get_dir(os.path.dirname(dirname), media)
        if parent == None:
            return None

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
        return item.create(current, parent, media)


    def commit(self):
        """
        Commit changes to the database. All changes in the internal list
        are done first.
        """
        t1 = time.time()
        changes = self.changes
        for function, arg1, args, kwargs in self.changes:
            # It could be possible that an item is added twice. But this is no
            # problem because the duplicate will be removed at the
            # next query. It can also happen that a dir is added because of
            # _getdir and because of the parser. We can't avoid that but the
            # db should clean itself up.
            if 'callback' in kwargs:
                callback = kwargs['callback']
                del kwargs['callback']
                callback(function(arg1, *args, **kwargs))
            else:
                function(arg1, *args, **kwargs)
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
        self._db.delete_object((entry['type'], entry['id']))


    def _query_dirname(self, **query):
        """
        A query to get all files in a directory. Special keyword 'dirname' in
        the query is used for that.
        """
        dirname = query['dirname']

        # find correct mountpoint
        for m in self._mountpoints:
            if dirname.startswith(m.directory):
                break

        # get parent item (may be None for client)
        parent = None
        if 'parent' in query:
            parent = query['parent']

        if not parent:
            parent = self._get_dir(dirname, m)

        if parent and parent.dbid:
            items = [ item.create(f, parent, m) for f in \
                      self._db.query(parent = parent.dbid) ]
        else:
            items = []

        # sort items based on url. The listdir is also sorted, that makes
        # checking much faster
        items.sort(lambda x,y: cmp(x.url, y.url))

        # TODO: this could block for cdrom drives and network filesystems. Maybe
        # put the listdir in a thread

        # TODO: use parent mtime to check if an update is needed. Maybe call
        # it scan time or something like that. Also make it an option so the
        # user can turn the feature off.
        pos = -1
        for pos, f in enumerate(util.listdir(dirname, m)):
            if pos == len(items):
                # new file at the end
                items.append(item.create(f, parent, m))
                continue
            while f > items[pos].url:
                # file deleted
                i = items[pos]
                items.remove(i)
                if not self.read_only:
                    # delete from database by adding it to the internal changes
                    # list. It will be deleted right before the next commit.
                    self.changes.append((self._delete, i, [], {}))
                # delete
            if f == items[pos].url:
                # same file
                continue
            # new file
            items.insert(pos, item.create(f, parent, m))

        if pos + 1 < len(items):
            # deleted files at the end
            if not self.read_only:
                for i in items[pos+1-len(items):]:
                    self.changes.append((self._delete, i, [], {}))
            items = items[:pos+1-len(items)]

        if self.changes:
            # need commit because some items were deleted from the db
            self.commit()

        if 'recursive' in query and query['recursive']:
            # recursive, replace the directories with the content of the dir
            # This can take a long time on a big hd, so we need to step to keep
            # the main loop alive.
            # FIXME: both the step() and the fact that this can take several
            # minutes is very bad. This should not be used at all. It can also
            # block the server in the monitoring when checking all mtimes.
            subdirs = [ x for x in items if x.isdir ]
            items = [ x for x in items if not x.isdir ]
            for subdir in subdirs:
                items += self._query_dirname(dirname=subdir.filename[:-1],
                                             parent=subdir, recursive=True)
            # step now
            kaa.notifier.step(False)
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
            parent = self._get_dir(dirname, m)
            if parent:
                dbentry = self._db.query(parent = parent.dbid, name=basename)
                if not dbentry:
                    dbentry = 'file://' + f
                else:
                    dbentry = dbentry[0]
            else:
                dbentry = basename
            items.append(item.create(dbentry, parent, m))
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
            # A query to monitor a media (mountpoint). Special keyword 'media' in
            # the query is used for that.
            for m in self._mountpoints:
                if m.device == kwargs['device']:
                    return m
            raise AttributeError('Unknown device' % kwargs['device'])
        return self._db.query(*args, **kwargs)


    def add_object(self, type, *args, **kwargs):
        """
        Add an object to the db. If the keyword 'vfs_immediately' is set, the
        object will be added now and the db will be locked until the next commit.
        To avoid locking, do not se the keyword, but this means that a requery on
        the object won't find it before the next commit.
        """
        if 'metadata' in kwargs:
            metadata = kwargs['metadata']
            if metadata:
                for key in self._db._object_types[type][1].keys():
                    if metadata.has_key(key) and metadata[key] != None:
                        kwargs[key] = metadata[key]
            del kwargs['metadata']

        if 'vfs_immediately' in kwargs:
            if len(self.changes):
                self.commit()
            del kwargs['vfs_immediately']
            return self._db.add_object(type, *args, **kwargs)

        self.changes.append((self._db.add_object, type, args, kwargs))
        if len(self.changes) > MAX_BUFFER_CHANGES:
            self.commit()


    def update_object(self, (type, id), *args, **kwargs):
        """
        Update an object to the db. If the keyword 'vfs_immediately' is set, the
        object will be updated now and the db will be locked until the next commit.
        To avoid locking, do not se the keyword, but this means that a requery on
        the object will return the old values.
        """
        if 'metadata' in kwargs:
            metadata = kwargs['metadata']
            if metadata:
                for key in self._db._object_types[type][1].keys():
                    if metadata.has_key(key) and metadata[key] != None:
                        kwargs[key] = metadata[key]
            del kwargs['metadata']

        if 'vfs_immediately' in kwargs:
            if len(self.changes):
                self.commit()
            del kwargs['vfs_immediately']
            return self._db.update_object((type, id), *args, **kwargs)

        self.changes.append((self._db.update_object, (type, id), args, kwargs))
        if len(self.changes) > MAX_BUFFER_CHANGES:
            self.commit()


    def register_object_type_attrs(self, type, *args, **kwargs):
        """
        Register a new object with attributes. Special keywords like name and
        mtime are added by default.
        """
        kwargs['name'] = (str, ATTR_KEYWORDS_FILENAME)
        # TODO: mtime may not e needed for subitems like tracks
        kwargs['overlay'] = (bool, ATTR_SIMPLE)
        kwargs['media'] = (int, ATTR_SIMPLE)
        if not type.startswith('track_'):
            kwargs['mtime'] = (int, ATTR_SIMPLE)
        return self._db.register_object_type_attrs(type, *args, **kwargs)
