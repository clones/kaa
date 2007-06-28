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
# Copyright (C) 2006 Dirk Meyer
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
from kaa.beacon.item import Item
from kaa.beacon.media import medialist
from kaa.beacon.db import Database as RO_Database

# get logging object
log = logging.getLogger('beacon.db')

MAX_BUFFER_CHANGES = 30

# Item generation mapping
from kaa.beacon.file import File as create_file
from kaa.beacon.item import create_item


class Database(RO_Database):
    """
    A kaa.db based database.
    """

    def __init__(self, dbdir):
        """
        Init function
        """
        super(Database,self).__init__(dbdir, None)

        # server lock when a client is doing something
        self.read_lock = False
        
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
            content = (str, ATTR_SIMPLE))

        # commit
        self._db.commit()


    # -------------------------------------------------------------------------
    # Database access
    #
    # The database functions are only called for the server.
    # (Except get_db_info which is only for debugging)
    # -------------------------------------------------------------------------

    def commit(self):
        """
        Commit changes to the database. All changes in the internal list
        are done first.
        """
        # db commit
        t1 = time.time()
        self._db.commit()
        t2 = time.time()

        # some time debugging
        log.info('db.commit %d items; kaa.db commit %.5f' % \
                 (len(changes), t2-t1)
        changes = self.changes
        self.changes = []

        # fire db changed signal
        self.signals['changed'].emit(changes)


    def add_object(self, type, metadata=None, **kwargs):
        """
        Add an object to the db.
        """
        if self.read_lock:
            raise IOError('database is locked')

        if metadata:
            for key in self._db._object_types[type][1].keys():
                if metadata.has_key(key) and metadata[key] != None and \
                       not key in kwargs:
                    kwargs[key] = metadata[key]

        result = self._db.add_object(type, **kwargs)
        self.changes.append((result['type'], result['id']))
        if len(self.changes) > MAX_BUFFER_CHANGES:
            self.commit()
        return result


    def update_object(self, (type, id), metadata=None, **kwargs):
        """
        Update an object to the db.
        """
        if self.read_lock:
            raise IOError('database is locked')
        
        if metadata:
            for key in self._db._object_types[type][1].keys():
                if metadata.has_key(key) and metadata[key] != None and \
                       not key == 'media':
                    kwargs[key] = metadata[key]

        if 'media' in kwargs:
            del kwargs['media']
        self._db.update_object((type, id), **kwargs)
        self.changes.append((type, id))
        if len(self.changes) > MAX_BUFFER_CHANGES:
            self.commit()


    def update_object_type(self, (type, id), new_type):
        if self.read_lock:
            raise IOError('database is locked')

        old_entry = self._db.query(type=type, id=id)
        if not old_entry:
            # already changed by something
            return None
        # FIXME: crashes with new ObjectRows code
        old_entry = dict(old_entry[0])

        # copy metadata to new object
        metadata = {}
        for key in self._db._object_types[new_type][1].keys():
            if not key == 'id' and key in old_entry:
                metadata[key] = old_entry[key]

        metadata = self._db.add_object(new_type, **metadata)
        new_beacon_id = (type, metadata['id'])

        # move all children to new parent
        for child in self._db.query(parent=(type, id)):
            log.warning('untested code: mode parent for %s' % child)
            id = (child['type'], child['id'])
            self._db.update_object(id, parent=new_beacon_id)

        # delete old and sync the db again
        self.delete_object((type, id))
        return metadata


    def register_object_type_attrs(self, type, *args, **kwargs):
        """
        Register a new object with attributes. Special keywords like name and
        mtime are added by default.
        """
        kwargs['name'] = (str, ATTR_KEYWORDS)
        # TODO: mtime may not e needed for subitems like tracks
        kwargs['overlay'] = (bool, ATTR_SIMPLE)
        kwargs['media'] = (int, ATTR_INDEXED)
        if not type.startswith('track_'):
            kwargs['mtime'] = (int, ATTR_SIMPLE)
            kwargs['image'] = (str, ATTR_SIMPLE)
        indices = [("name", "parent_type", "parent_id")]
        return self._db.register_object_type_attrs(type, indices, *args, **kwargs)


    def delete_object(self, item_or_type_id_list):
        if self.read_lock:
            raise IOError('database is locked')
        for id in self._delete(item_or_type_id_list):
            self.changes.append(id)
        if len(self.changes) > MAX_BUFFER_CHANGES:
            self.commit()


    def delete_media(self, id):
        """
        Delete media with the given id.
        """
        log.info('delete media %s', id)
        for child in self._db.query(media = id):
            self._db.delete_object((str(child['type']), child['id']))
        self._db.delete_object(('media', id))
        self._db.commit()


    # -------------------------------------------------------------------------
    # Internal functions
    # -------------------------------------------------------------------------


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
