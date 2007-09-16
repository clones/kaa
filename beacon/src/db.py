# -*- coding: iso-8859-1 -*-
# -----------------------------------------------------------------------------
# db.py - Beacon database
# -----------------------------------------------------------------------------
# $Id$
#
# TODO: o Make it possible to override create_file
#
# -----------------------------------------------------------------------------
# kaa.beacon - A virtual filesystem with metadata
# Copyright (C) 2006-2007 Dirk Meyer
#
# First Edition: Dirk Meyer <dischi@freevo.org>
# Maintainer:    Dirk Meyer <dischi@freevo.org>
#
# Please see the file AUTHORS for a complete list of authors.
#
# This library is free software; you can redistribute it and/or modify
# it under the terms of the GNU Lesser General Public License version
# 2.1 as published by the Free Software Foundation.
#
# This library is distributed in the hope that it will be useful, but
# WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
# Lesser General Public License for more details.
#
# You should have received a copy of the GNU Lesser General Public
# License along with this library; if not, write to the Free Software
# Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA
# 02110-1301 USA
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
from media import medialist

# get logging object
log = logging.getLogger('beacon.db')

MAX_BUFFER_CHANGES = 30

# Item generation mapping
from file import File
from item import Item

# The db uses the following helper functions to create the correct item

def create_item(data, parent):
    """
    Create an Item that is neither dir nor file.
    """
    data = dict(data)
    dbid = (data['type'], data['id'])
    if 'url' in data:
        # url is stored in the data
        return Item(dbid, data['url'], data, parent, parent._beacon_media)
    if '://' in data['name']:
        # url is stored in the name (remote items in directory)
        return Item(dbid, data['name'], data, parent, parent._beacon_media)

    # generate url based on name and parent url
    url = parent.url
    if data['name']:
        if parent.url.endswith('/'):
            url = parent.url + data['name']
        else:
            url = parent.url + '/' + data['name']
    if data.get('scheme'):
        url = data.get('scheme') + url[url.find('://')+3:]
    return Item(dbid, url, data, parent, parent._beacon_media)


def create_file(data, parent, overlay=False, isdir=False):
    """
    Create a file or directory
    """
    return File(data, parent, overlay, isdir)


def create_directory(data, parent):
    """
    Create a directory
    """
    return create_file(data, parent, isdir=True)


def create_by_type(data, parent, overlay=False, isdir=False):
    """
    Create file, directory or any other kind of item.
    If the data indicates it is not a file or the parent is not
    a directory, make it an Item, not a File.
    """
    if (data.get('name').find('://') > 0) or (parent and not parent.isdir()):
        return create_item(data, parent)
    return create_file(data, parent, overlay, isdir)


class Database(object):
    """
    A kaa.db based database.
    """

    # functions that will be given by the server
    delete_object = add_object = commit = None

    def __init__(self, dbdir):
        """
        Init function
        """
        # internal db dir, it contains the real db and the
        # overlay dir for the beacon
        self._db_directory = dbdir

        # handle changes in a list and add them to the database
        # on commit.
        self.changes = []

        # create db
        if not os.path.isdir(self._db_directory):
            os.makedirs(self._db_directory)
        self._db = db.Database(self._db_directory + '/db')

        self.signals = {
            'changed': kaa.notifier.Signal()
            }


    def get_directory(self):
        """
        Get main beacon directory.
        """
        return self._db_directory


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
        qlen = len(query)
        if not 'media' in query:
            # query only media we have right now
            query['media'] = db.QExpr('in', medialist.get_all_beacon_ids())
        else:
            if query['media'] == 'ignore':
                del query['media']
            qlen -= 1

        # do query based on type
        if 'filename' in query and qlen == 1:
            fname = os.path.realpath(query['filename'])
            return self.query_filename(fname)
        if 'id' in query and qlen == 1:
            return self._db_query_id(query['id'])
        if 'parent' in query and 'recursive' in query and qlen == 2:
            if not query['parent']._beacon_isdir:
                raise AttributeError('parent is no directory')
            return self._db_query_dir_recursive(query['parent'])
        if 'parent' in query:
            if qlen == 1:
                if query['parent']._beacon_isdir:
                    return self._db_query_dir(query['parent'])
            query['parent'] = query['parent']._beacon_id
        if 'attr' in query:
            return self._db_query_attr(query)
        if 'type' in query and query['type'] == 'media':
            return self._db.query(**query)
        return self._db_query_raw(query)


    def query_media(self, media):
        """
        Get media information.
        """
        if hasattr(media, 'id'):
            # object is a media object
            id = media.id
        else:
            # object is only an id
            id = media
            media = None
        result = self._db.query(type="media", name=id)
        if not result:
            return None
        result = result[0]
        if not media:
            return result
        # TODO: it's a bit ugly to set url here, but we have no other choice
        media.url = result['content'] + '://' + media.mountpoint
        media.overlay = os.path.join(self._db_directory, id)
        dbid = ('media', result['id'])
        media._beacon_id = dbid
        root = self._db.query(parent=dbid)[0]
        if root['type'] == 'dir':
            media.root = create_directory(root, media)
        else:
            media.root = create_item(root, media)
        return result


    @kaa.notifier.yield_execution()
    def _db_query_dir(self, parent):
        """
        A query to get all files in a directory. The parameter parent is a
        directort object.
        """
        if parent._beacon_islink:
            # WARNING: parent is a link, we need to follow it
            dirname = os.path.realpath(parent.filename)
            parent = self.query_filename(dirname)
            if not parent._beacon_isdir:
                # oops, this is not directory anymore, return nothing
                yield []
        else:
            dirname = parent.filename[:-1]

        listing = parent._beacon_listdir(async=True)

        if isinstance(listing, kaa.notifier.InProgress):
            # oops, something takes more time than we had in mind,
            yield listing
            # when we reach this point, we can continue
            listing = listing()

        items = []
        if parent._beacon_id:
            items = [ create_by_type(i, parent, isdir=i['type'] == 'dir') \
                      for i in self._db.query(parent = parent._beacon_id) ]

        # sort items based on name. The listdir is also sorted by name,
        # that makes checking much faster
        items.sort(lambda x,y: cmp(x._beacon_name, y._beacon_name))

        # TODO: use parent mtime to check if an update is needed. Maybe call
        # it scan time or something like that. Also make it an option so the
        # user can turn the feature off.

        pos = -1

        # If we have a delete_object function we will use it. This means
        # we have to wait for a lock. The server needs to provide
        # the read_lock variable. I known this is ugly but I do not
        # want to duplicate this whole function just for this.
        while self.delete_object and self.read_lock.is_locked():
            yield self.read_lock.yield_unlock()

        pos = -1
        for f, fullname, overlay, stat_res in listing[0]:
            pos += 1
            isdir = stat.S_ISDIR(stat_res[stat.ST_MODE])
            if pos == len(items):
                # new file at the end
                if isdir:
                    if not overlay:
                        items.append(create_directory(f, parent))
                    continue
                items.append(create_file(f, parent, overlay))
                continue
            while pos < len(items) and f > items[pos]._beacon_name:
                # file deleted
                i = items[pos]
                if not i.isdir() and not i.isfile():
                    # A remote URL in the directory
                    pos += 1
                    continue
                items.remove(i)
                if self.delete_object:
                    # delete from database by adding it to the internal changes
                    # list. It will be deleted right before the next commit.
                    self.delete_object(i)
            if pos < len(items) and f == items[pos]._beacon_name:
                # same file
                continue
            # new file
            if isdir:
                if not overlay:
                    items.insert(pos, create_directory(f, parent))
                continue
            items.insert(pos, create_file(f, parent, overlay))

        if pos + 1 < len(items):
            # deleted files at the end
            for i in items[pos+1-len(items):]:
                if not i.isdir() and not i.isfile():
                    # A remote URL in the directory
                    continue
                items.remove(i)
                if self.delete_object:
                    # delete from database by adding it to the internal changes
                    # list. It will be deleted right before the next commit.
                    self.delete_object(i)

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
            parent = self.query_filename(dirname)
            if not parent._beacon_isdir:
                # oops, this is not directory anymore, return nothing
                yield []
        else:
            dirname = parent.filename[:-1]

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
                    child = create_directory(i, parent)
                    if not child._beacon_islink:
                        directories.append(child)
                else:
                    items.append(create_by_type(i, parent))
            if time.time() > timer + 0.1:
                # we are in async mode and already use too much time.
                # call yield YieldContinue at this point to continue
                # later.
                timer = time.time()
                yield kaa.notifier.YieldContinue

        # sort items based on name. The listdir is also sorted by name,
        # that makes checking much faster
        items.sort(lambda x,y: cmp(x._beacon_name, y._beacon_name))
        yield items


    def _db_query_id(self, (type, id), cache=None):
        """
        Return item based on (type,id). Use given cache if provided.
        """
        i = self._db.query(type=type, id=id)[0]
        # now we need a parent
        if i['name'] == '':
            # root node found, find correct mountpoint
            m = medialist.get_by_beacon_id(i['parent'])
            if not m:
                raise AttributeError('bad media %s' % str(i['parent']))
            return create_directory(i, m)

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
            return create_directory(i, parent)
        return create_by_type(i, parent)


    def _db_query_attr(self, query):
        """
        A query to get a list of possible values of one attribute. Special
        keyword 'attr' the query is used for that. This query will not return
        a list of items.
        """
        attr = query['attr']
        del query['attr']

        result = self._db.query(attrs=[attr], distinct=True, **query)
        result = [ x[attr] for x in result if x[attr] ]

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
        # FIXME: this function needs optimizing; adds at least 6 times the
        # overhead on top of kaa.db.query
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
                result.append(create_directory(r, parent))
            else:
                # file or something else
                result.append(create_by_type(r, parent))

            counter += 1
            if not counter % 50 and time.time() > timer + 0.05:
                # we are in async mode and already use too much time.
                # call yield YieldContinue at this point to continue
                # later.
                timer = time.time()
                yield kaa.notifier.YieldContinue

        if not 'keywords' in query:
            # sort results by url (name is not unique) and return
            result.sort(lambda x,y: cmp(x.url, y.url))
        yield result


    def query_filename(self, filename):
        """
        Return item for filename, can't be in overlay. This function will
        never return an InProgress object.
        """
        dirname = os.path.dirname(filename)
        basename = os.path.basename(filename)
        m = medialist.get_by_directory(filename)
        if not m:
            raise AttributeError('mountpoint not found')

        if (os.path.isdir(filename) and \
            m != medialist.get_by_directory(dirname)) or filename == '/':
            # the filename is the mountpoint itself
            e = self._db.query(parent=m._beacon_id, name='')
            return create_directory(e[0], m)
        parent = self._query_filename_get_dir(dirname, m)
        if parent._beacon_id:
            # parent is a valid db item, query
            e = self._db.query(parent=parent._beacon_id, name=basename)
            if e:
                # entry is in the db
                return create_file(e[0], parent, isdir=e[0]['type'] == 'dir')
        return create_file(basename, parent, isdir=os.path.isdir(filename))


    def _query_filename_get_dir(self, dirname, media):
        """
        Get database entry for the given directory. Called recursive to
        find the current entry. Do not cache results, they could change.
        """
        if dirname == media.mountpoint or dirname +'/' == media.mountpoint:
            # we know that '/' is in the db
            c = self._db.query(type="dir", name='', parent=media._beacon_id)[0]
            return create_directory(c, media)

        if dirname == '/':
            raise RuntimeError('media %s not found' % media)

        parent = self._query_filename_get_dir(os.path.dirname(dirname), media)
        name = os.path.basename(dirname)

        if not parent._beacon_id:
            return create_directory(name, parent)

        c = self._db.query(type="dir", name=name, parent=parent._beacon_id)
        if c:
            return create_directory(c[0], parent)

        if not self.add_object:
            # we have no add_object function. This means we have
            # to return a dummy object (client)
            return create_directory(name, parent)
        # add object to the database.
        # NOTICE: this function will change the database even when
        # the db is locked. I do not see a good way around it and
        # it should not happen often. To make the write lock a very
        # short time we commit just after adding.
        c = self.add_object("dir", name=name, parent=parent)
        if self.read_lock.is_locked():
            # commit changes
            self.commit()
        return create_directory(c, parent)


    # -------------------------------------------------------------------------
    # Database access
    # -------------------------------------------------------------------------

    def get_db_info(self):
        """
        Returns information about the database.  Look at
        kaa.db.Database.get_db_info() for more details.
        """
        return self._db.get_db_info()
