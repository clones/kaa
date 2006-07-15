# -*- coding: iso-8859-1 -*-
# -----------------------------------------------------------------------------
# db.py - Beacon database
# -----------------------------------------------------------------------------
# $Id$
#
# TODO: o Make it possible to override create_file and create_dir
#       o Support tracks and other non file based items
#
# -----------------------------------------------------------------------------
# kaa-beacon - A virtual filesystem with metadata
# Copyright (C) 2006 Dirk Meyer
#
# First Edition: Dirk Meyer <dischi@freevo.org>
# Maintainer:    Dirk Meyer <dischi@freevo.org>
#
# Please see the file AUTHORS for a complete list of authors.
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
import stat
import threading
import logging
import time

# kaa imports
import kaa.notifier
from kaa import db
from kaa.db import *

# beacon imports
from item import Item
from hwmon import medialist

# get logging object
log = logging.getLogger('beacon.db')

MAX_BUFFER_CHANGES = 30

# Item generation mapping
from directory import Directory as create_dir
from file import File as create_file
from item import create_item

class Database(object):
    """
    A kaa.db based database.
    """

    def __init__(self, dbdir, client):
        """
        Init function
        """
        # internal db dir, it contains the real db and the
        # overlay dir for the beacon
        self.dbdir = dbdir

        # remember client
        # no client == server == write access
        self.client = client

        # handle changes in a list and add them to the database
        # on commit.
        self.changes = []

        # create db
        if not os.path.isdir(self.dbdir):
            os.makedirs(self.dbdir)
        self._db = db.Database(self.dbdir + '/db')

        self.signals = {
            'changed': kaa.notifier.Signal()
            }

        if self.client:
            # client mode, nothing more to do
            return
        
        # register basic types
        self._db.register_object_type_attrs("dir",
            # This multi-column index optimizes queries on (name,parent) which
            # is done for every object add/update, so must be fast.  All
            # object types will have this combined index.
            [("name", "parent_type", "parent_id")],
            name = (str, ATTR_KEYWORDS),
            overlay = (bool, ATTR_SIMPLE),
            media = (int, ATTR_INDEXED),
            mtime = (int, ATTR_SIMPLE))

        self._db.register_object_type_attrs("file",
            [("name", "parent_type", "parent_id")],
            name = (str, ATTR_KEYWORDS),
            overlay = (bool, ATTR_SIMPLE),
            media = (int, ATTR_INDEXED),
            mtime = (int, ATTR_SIMPLE))

        self._db.register_object_type_attrs("media",
            [("name", "parent_type", "parent_id")],
            name = (str, ATTR_KEYWORDS),
            title = (unicode, ATTR_KEYWORDS),
            overlay = (bool, ATTR_SIMPLE),
            length = (int, ATTR_SIMPLE),
            content = (str, ATTR_SIMPLE))

        # commit
        self._db.commit()


    # -------------------------------------------------------------------------
    # Query functions
    #
    # The query functions can modify the database when in server mode. E.g.
    # a directory query could detect deleted files and will delete them in
    # the database. In client mode, the query functions will use the database
    # read only.
    # -------------------------------------------------------------------------

    def query(self, **query):
        """
        Main query function. This function will call one of the specific
        query functions ins this class depending on the query. This function
        may raise an AsyncProcess exception.
        """
        # make sure db is ok
        if not self.client:
            self.commit()

        qlen = len(query)
        if not 'media' in query:
            # query only media we have right now
            query['media'] = db.QExpr('in', [ m._beacon_id[1] for m in medialist ])
        else:
            if query['media'] == 'ignore':
                del query['media']
            qlen -= 1
            
        # do query based on type
        if 'filename' in query and qlen == 1:
            return self._db_query_filename(query['filename'])
        if 'id' in query and qlen == 1:
            return self._db_query_id(query['id'])
        if 'parent' in query:
            if qlen == 1:
                if query['parent']._beacon_isdir:
                    return self._db_query_dir(query['parent'])
            query['parent'] = query['parent']._beacon_id
        if 'parent' in query and 'recursive' in query and qlen == 2:
            if not query['parent']._beacon_isdir:
                raise AttributeError('parent is no directory')
            return self._db_query_dir_recursive(query['parent'])
        if 'attr' in query:
            return self._db_query_attr(query)
        if 'type' in query and query['type'] == 'media':
            m = self._db.query(**query)
            if m:
                return m[0]
            return None
        return self._db_query_raw(query)
    

    def query_media(self, id, media):
        """
        Get media and the root filesystem. If 'media' is None,
        the root filesystem is also None. You have to pass a media
        object to get media and root filesystem.
        Returns dbinfo, beacon_id, root
        """
        result = self._db.query(type="media", name=id)
        if not result:
            return None, None, None
        result = result[0]
        id = ('media', result['id'])
        if not media:
            return result, id, None
        # TODO: it's a bit ugly to set url here, but we have no other choice
        media.url = result['content'] + ':/' + media.mountpoint[:-1]
        root = self._db.query(parent=id)[0]
        if root['type'] == 'dir':
            return result, id, create_dir(root, media)
        return result, id, create_item(root, media)

        
    @kaa.notifier.yield_execution()
    def _db_query_dir(self, parent):
        """
        A query to get all files in a directory. The parameter parent is a
        directort object.
        """
        if parent._beacon_islink:
            # WARNING: parent is a link, we need to follow it
            dirname = os.path.realpath(parent.filename)
            parent = self._db_query_filename(dirname)
            if not parent._beacon_isdir:
                # oops, this is not directory anymore, return nothing
                yield []
        else:
            dirname = parent.filename[:-1]

        listing = parent._beacon_listdir(async=self.client)
        
        if isinstance(listing, kaa.notifier.InProgress):
            # oops, something takes more time than we had in mind,
            yield listing
            # when we reach this point, we can continue
            listing = listing()

        items = []
        if parent._beacon_id:
            # XXX: This loop is a performance hotspot, accounting for nearly
            # 70% of execution time in this function.  The time in this loop
            # is comprised of about 60-70% for the db query, and the rest in
            # File/Directory object creation.  Of the query itself, 70% of
            # that time is spent normalizing the query results.  So if
            # normalization can be deferred, we can get results to the
            # caller .7*.7*.7 =~ 35% faster.
            for i in self._db.query(parent = parent._beacon_id):
                if i['type'] == 'dir':
                    items.append(create_dir(i, parent))
                else:
                    items.append(create_file(i, parent))

        # sort items based on name. The listdir is also sorted by name,
        # that makes checking much faster
        items.sort(lambda x,y: cmp(x._beacon_name, y._beacon_name))

        # TODO: use parent mtime to check if an update is needed. Maybe call
        # it scan time or something like that. Also make it an option so the
        # user can turn the feature off.

        # XXX: Most of the remaining time for this function is in this loop.
        # About 25%.  (Assuming stat results are cached by the filesystem so
        # no disk access is needed.)
        pos = -1

        for pos, (f, fullname, overlay, stat_res) in enumerate(listing[0]):
            isdir = stat.S_ISDIR(stat_res[stat.ST_MODE])
            if pos == len(items):
                # new file at the end
                if isdir:
                    if not overlay:
                        items.append(create_dir(f, parent))
                    continue
                items.append(create_file(f, parent, overlay))
                continue
            while pos < len(items) and f > items[pos]._beacon_name:
                # file deleted
                i = items[pos]
                items.remove(i)
                if not self.client:
                    # no client == server == write access
                    # delete from database by adding it to the internal changes
                    # list. It will be deleted right before the next commit.
                    self.changes.append(('delete', i, {}))
                # delete
            if pos < len(items) and f == items[pos]._beacon_name:
                # same file
                continue
            # new file
            if isdir:
                if not overlay:
                    items.insert(pos, create_dir(f, parent))
                continue
            items.insert(pos, create_file(f, parent, overlay))

        if pos + 1 < len(items):
            # deleted files at the end
            if not self.client:
                # no client == server == write access
                for i in items[pos+1-len(items):]:
                    self.changes.append(('delete', i, {}))
            items = items[:pos+1-len(items)]

        if self.changes:
            # need commit because some items were deleted from the db
            self.commit()

        # no need to sort the items again, they are already sorted based
        # on name, let us keep it that way. And name is unique in a directory.
        # items.sort(lambda x,y: cmp(x.url, y.url))
        yield items


    @kaa.notifier.yield_execution()
    def _db_query_dir_recursive(self, parent):
        """
        Return all files in the directory 'parent' including files in
        subdirectories (and so on). The directories itself will not be
        returned. If a subdir is a softlink, it will be skipped. This
        query does not check if the files are still there and if the
        database list is up to date.
        """
        if parent._beacon_islink:
            # WARNING: parent is a link, we need to follow it
            dirname = os.path.realpath(parent.filename)
            parent = self._db_query_filename(dirname)
            if not parent._beacon_isdir:
                # oops, this is not directory anymore, return nothing
                yield []
        else:
            dirname = parent.filename[:-1]

        async = False
        if self.client:
            async = True
            timer = time.time()

        items = []
        # A list of all directories we will look at. If a link is in the
        # directory it will be ignored.
        directories = [ parent ]
        while directories:
            parent = directories.pop(0)
            if not parent._beacon_id:
                continue
            for i in self._db.query(parent = parent._beacon_id):
                if i['type'] == 'dir':
                    child = create_dir(i, parent)
                    if not child._beacon_islink:
                        directories.append(child)
                else:
                    items.append(create_file(i, parent))
            if async and time.time() > timer + 0.1:
                # we are in async mode and already use too much time.
                # call yield YieldContinue at this point to continue
                # later.
                timer = time.time()
                yield kaa.notifier.YieldContinue

        # sort items based on name. The listdir is also sorted by name,
        # that makes checking much faster
        items.sort(lambda x,y: cmp(x._beacon_name, y._beacon_name))
        yield items


    def _db_query_filename(self, filename):
        """
        Return item for filename, can't be in overlay
        """
        dirname = os.path.dirname(filename)
        basename = os.path.basename(filename)
        m = medialist.mountpoint(filename)
        if not m:
            raise AttributeError('mountpoint not found')
        if os.path.isdir(filename) and not m == medialist.mountpoint(dirname):
            # the filename is the mountpoint itself
            e = self._db.query(parent=m._beacon_id, name='')
            return create_dir(e[0], m)
        parent = self._get_dir(dirname, m)
        if parent._beacon_id:
            # parent is a valid db item, query
            e = self._db.query(parent=parent._beacon_id, name=basename)
            if e:
                # entry is in the db
                basename = e[0]
        if os.path.isdir(filename):
            return create_dir(basename, parent)
        return create_file(basename, parent)


    def _db_query_id(self, (type, id), cache=None):
        """
        Return item based on (type,id). Use given cache if provided.
        """
        i = self._db.query(type=type, id=id)[0]
        # now we need a parent
        if i['name'] == '':
            # root node found, find correct mountpoint
            m = medialist.beacon_id(i['parent'])
            if not m:
                raise AttributeError('bad media %s' % str(i['parent']))
            return create_dir(i, m)

        # query for parent
        pid = i['parent']
        if cache is not None and pid in cache:
            parent = cache[pid]
        else:
            parent = self._db_query_id(pid)
            if cache is not None:
                cache[pid] = parent

        if i['type'] == 'dir':
            # it is a directory, make a dir item
            return create_dir(i, parent)
        if parent._beacon_isdir:
            # parent is dir, this item is not
            return create_file(i, parent)
        # neither dir nor file, something else
        return create_item(i, parent)


    def _db_query_attr(self, query):
        """
        A query to get a list of possible values of one attribute. Special
        keyword 'attr' the query is used for that. This query will not return
        a list of items.
        """
        attr = query['attr']
        del query['attr']

        result = self._db.query_raw(attrs=[attr], distinct=True, **query)[1]
        result = [ x[1] for x in result if x[1] ]

        # sort results and return
        result.sort()
        return result


    @kaa.notifier.yield_execution()
    def _db_query_raw(self, query):
        """
        Do a 'raw' query. This means to query the database and create
        a list of items from the result. The items will have a complete
        parent structure. For files / directories this function won't check
        if they are still there.
        """
        result = []
        cache = {}
        counter = 0
        timer = time.time()

        for media in medialist:
            cache[media._beacon_id] = media
            cache[media.root._beacon_id] = media.root

        for r in self._db.query(**query):
            
            # get parent
            pid = r['parent']
            if pid in cache:
                parent = cache[pid]
            else:
                parent = self._db_query_id(pid, cache)
                cache[pid] = parent

            # create item
            if r['type'] == 'dir':
                # it is a directory, make a dir item
                result.append(create_dir(r, parent))
            elif parent._beacon_isdir:
                # parent is dir, this item is not
                result.append(create_file(r, parent))
            else:
                # neither dir nor file, something else
                result.append(create_item(r, parent))

            counter += 1
            if self.client and not counter % 50 and time.time() > timer + 0.05:
                # we are in async mode and already use too much time.
                # call yield YieldContinue at this point to continue
                # later.
                timer = time.time()
                yield kaa.notifier.YieldContinue

        if not 'keywords' in query:
            # sort results by url (name is not unique) and return
            result.sort(lambda x,y: cmp(x.url, y.url))
        yield result

        
    # -------------------------------------------------------------------------
    # Database access
    #
    # The database functions are only called for the server.
    # (Except get_db_info which is only for debugging)
    # -------------------------------------------------------------------------

    def commit(self, force=False):
        """
        Commit changes to the database. All changes in the internal list
        are done first.
        """
        if self.client or (not self.changes and not force):
            return

        # Before we start with the commit, we make sure that all items we want
        # to add are not in the db already.
        for pos, (function, arg1, kwargs) in enumerate(self.changes):
            if not function == 'add' or not 'parent' in kwargs or \
                   not 'name' in kwargs:
                continue
            # check the db
            result = self._db.query(name=kwargs['name'],
                                    parent=kwargs['parent'])
            if not result:
                continue
            # change 'add' to 'update'
            log.info('switch from add to update for %s', kwargs['name'])
            result = result[0]
            if 'callback' in kwargs:
                callback = kwargs['callback']
                del kwargs['callback']
                callback(result)
            self.changes[pos] = ('update', result['type'], result['id'], kwargs)

        # Now we did everything we can to make it as fast as possible. Let
        # us start with the real db changes now

        # get time for debugging
        t1 = time.time()
        # set internal variables
        changes = self.changes
        changed_id = []
        self.changes = []
        callbacks = []

        # NOTE: Database will be locked now

        # walk through the list of changes
        for function, arg1, kwargs in changes:
            callback = None
            if 'callback' in kwargs:
                callback = kwargs['callback']
                del kwargs['callback']
            if function == 'delete':
                # delete items and all subitems from the db. The delete function
                # will return all ids deleted, callbacks are not allowed, so
                # we can just continue
                changed_id.extend(self._delete(arg1))
                continue
            if function == 'update':
                try:
                    result = self._db.update_object(arg1, **kwargs)
                    changed_id.append(arg1)
                except Exception, e:
                    log.error('%s not in the db: %s: %s' % (arg1, e, kwargs))
                    result = None
            elif function == 'add':
                # arg1 is the type, kwargs should contain parent and name, the
                # result is the return of a query, so it has (type, id)
                result = self._db.add_object(arg1, **kwargs)
                changed_id.append((result['type'], result['id']))
            else:
                # programming error, this should never happen
                log.error('unknown change <%s>' % function)
                continue
            if callback and result is not None:
                callbacks.append((callback, result))

        # db commit
        t2 = time.time()
        self._db.commit()
        t3 = time.time()

        # NOTE: Database is unlocked again

        # some time debugging
        log.info('db.commit %d items; %.5fs (kaa.db commit %.5f / %.2f%%)' % \
                 (len(changes), t3-t1, t3-t2, (t3-t2)/(t3-t1)*100.0))
        # now call all callbacks
        for callback, result in callbacks:
            callback(result)
        # fire db changed signal
        self.signals['changed'].emit(changed_id)


    def get_object(self, name, parent):
        """
        Get the object with the given type, name and parent. This function will
        look at the pending commits and also in the database.
        """
        for func, type, kwargs  in self.changes:
            if func == 'add' and 'name' in kwargs and kwargs['name'] == name \
                   and 'parent' in kwargs and kwargs['parent'] == parent:
                self.commit()
                break
        result = self._db.query(name=name, parent=parent)
        if result:
            return result[0]
        return None


    def add_object(self, type, metadata=None, beacon_immediately=False,
                   **kwargs):
        """
        Add an object to the db. If the keyword 'beacon_immediately' is set,
        the object will be added now and the db will be locked until the next
        commit. To avoid locking, do not se the keyword, but this means that a
        requery on the object won't find it before the next commit.
        """
        if metadata:
            for key in self._db._object_types[type][1].keys():
                if metadata.has_key(key) and metadata[key] != None and \
                       not key in kwargs:
                    kwargs[key] = metadata[key]

        if beacon_immediately:
            self.commit()
            return self._db.add_object(type, **kwargs)
        self.changes.append(('add', type, kwargs))
        if len(self.changes) > MAX_BUFFER_CHANGES:
            self.commit()


    def update_object(self, (type, id), metadata=None,
                      beacon_immediately=False, **kwargs):
        """
        Update an object to the db. If the keyword 'beacon_immediately' is set,
        the object will be updated now and the db will be locked until the next
        commit. To avoid locking, do not se the keyword, but this means that a
        requery on the object will return the old values.
        """
        if metadata:
            for key in self._db._object_types[type][1].keys():
                if metadata.has_key(key) and metadata[key] != None and \
                       not key == 'media':
                    kwargs[key] = metadata[key]

        if 'media' in kwargs:
            del kwargs['media']
        if isinstance(kwargs.get('media'), str):
            raise SystemError
        self.changes.append(('update', (type, id), kwargs))
        if len(self.changes) > MAX_BUFFER_CHANGES or beacon_immediately:
            self.commit()


    def update_object_type(self, (type, id), new_type):
        old_entry = self._db.query(type=type, id=id)
        if not old_entry:
            # already changed by something
            return None
        old_entry = old_entry[0]

        # copy metadata to new object
        metadata = {}
        for key in self._db._object_types[new_type][1].keys():
            if not key == 'id' and key in old_entry:
                metadata[key] = old_entry[key]
        # add object to db keep the db in sync
        self.commit()
        # FIXME: media?
        metadata = self._db.add_object(new_type, **metadata)
        new_beacon_id = (type, metadata['id'])
        self._db.commit()

        # move all children to new parent
        for child in self._db.query(parent=(type, id)):
            log.warning('untested code: mode parent for %s' % child)
            id = (child['type'], child['id'])
            self._db.update_object(id, parent=new_beacon_id)

        # delete old and sync the db again
        self.delete_object((type, id))
        self.commit()
        return metadata


    def delete_object(self, (type, id), beacon_immediately=False):
        self.changes.append(('delete', (type, id), {}))
        if len(self.changes) > MAX_BUFFER_CHANGES or beacon_immediately:
            self.commit()


    def object_types(self):
        """
        Return the list of object types
        """
        return self._db._object_types


    def register_object_type_attrs(self, type, *args, **kwargs):
        """
        Register a new object with attributes. Special keywords like name and
        mtime are added by default.
        """
        kwargs['name'] = (str, ATTR_KEYWORDS_FILENAME)
        # TODO: mtime may not e needed for subitems like tracks
        kwargs['overlay'] = (bool, ATTR_SIMPLE)
        kwargs['media'] = (int, ATTR_INDEXED)
        if not type.startswith('track_'):
            kwargs['mtime'] = (int, ATTR_SIMPLE)
        indices = [("name", "parent_type", "parent_id")]
        return self._db.register_object_type_attrs(type, indices, *args,
                                                   **kwargs)


    def get_db_info(self):
        """
        Returns information about the database.  Look at
        kaa.db.Database.get_db_info() for more details.
        """
        return self._db.get_db_info()


    # -------------------------------------------------------------------------
    # Internal functions
    # -------------------------------------------------------------------------

    def _get_dir(self, dirname, media):
        """
        Get database entry for the given directory. Called recursive to
        find the current entry. Do not cache results, they could change.
        """
        if dirname == media.mountpoint:
            # we know that '/' is in the db
            current = self._db.query(type="dir", name='', parent=media._beacon_id)[0]
            return create_dir(current, media)

        parent = self._get_dir(os.path.dirname(dirname), media)
        name = os.path.basename(dirname)

        if not parent._beacon_id:
            return create_dir(name, parent)

        current = self._db.query(type="dir", name=name,
                                 parent=parent._beacon_id)
        if not current and self.client:
            return create_dir(name, parent)

        if not current:
            current = self._db.add_object("dir", name=name,
                                          parent=parent._beacon_id,
                                          media=media._beacon_id[1])
            self._db.commit()
        else:
            current = current[0]
        return create_dir(current, parent)


    def _delete(self, entry):
        """
        Delete item with the given id from the db and all items with that
        items as parent (and so on). To avoid internal problems, make sure
        commit is called just after this function is called.
        """
        log.info('delete %s', entry)
        if isinstance(entry, Item):
            entry = entry._beacon_id
        deleted = [ entry ]
        for child in self._db.query(parent = entry):
            deleted.extend(self._delete((child['type'], child['id'])))

        # FIXME: if the item has a thumbnail, delete it!
        self._db.delete_object(entry)
        return deleted


