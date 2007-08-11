# -*- coding: iso-8859-1 -*-
# -----------------------------------------------------------------------------
# client.py - Client interface for Beacon
# -----------------------------------------------------------------------------
# $Id$
#
# This is the client interface to beacon. The server needs to be running.
# To use the server a Client object must be created. Once created, it is
# possible to start a query on the client.
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


# Python imports
import os
import copy
import logging

# kaa imports
import kaa
import kaa.rpc
import kaa.strutils
from kaa.weakref import weakref
from kaa.notifier import OneShotTimer, Signal

# kaa.beacon imports
from db import Database
from query import Query
from media import medialist
from item import Item

# get logging object
log = logging.getLogger('beacon')

DISCONNECTED = 'disconnected'
CONNECTING   = 'connecting'
CONNECTED    = 'connected'
SHUTDOWN     = 'shutdown'

class ConnectError(Exception):
    pass

class Client(object):
    """
    Beacon client. This client uses the db read only and needs a server on
    the same machine doing the file scanning and changing of the db.
    """
    def __init__(self):
        self._db = None

        self.signals = {
            'connect'   : Signal(),
            'disconnect': Signal(),
            'media.add' : Signal(),
            'media.remove': Signal()
        }

        # internal list of active queries
        self._queries = []
        # internal list of items to update
        self._changed = []
        # add ourself to shutdown handler for correct disconnect
        kaa.signals['shutdown'].connect(self._shutdown)
        self.status = DISCONNECTED
        self._connect()


    def __repr__(self):
        """
        Convert object to string (usefull for debugging)
        """
        return '<beacon.Client>'


    # -------------------------------------------------------------------------
    # Public API
    # -------------------------------------------------------------------------

    def get(self, filename):
        """
        Return an object for the given filename.
        """
        filename = os.path.realpath(filename)
        if not os.path.exists(filename):
            raise OSError('no such file or directory %s' % filename)
        return Query(self, filename=filename).get()


    def query(self, **query):
        """
        Query the database.
        """
        if not kaa.notifier.is_mainthread():
            # sqlite db was opened in the mainthread, so we must perform
            # all our queries there as well.
            cb = kaa.notifier.MainThreadCallback(self.query)
            cb.set_async(False)
            return cb(**query)

        result = Query(self, **query)
        self._queries.append(weakref(result))
        return result


    def add_item(self, url, type, parent, **kwargs):
        """
        Add non-file item item.
        """
        if self.status == DISCONNECTED:
            return None
        if isinstance(url, unicode):
            url = kaa.strutils.unicode_to_str(url)
        kwargs['scheme'] = url[:url.find('://')]
        kwargs['name'] = url
        i = Item(None, url, kwargs, parent, parent._beacon_media)
        rpc = self.rpc('item.create', type=type, parent=parent._beacon_id, **kwargs)
        rpc.connect(i._beacon_database_update)
        return i


    def delete_item(self, item):
        """
        Delete non-file item item.
        """
        self.rpc('item.delete', item._beacon_id)


    def monitor(self, directory):
        """
        Monitor a directory with subdirectories for changes. This is done in
        the server and will keep the database up to date.
        """
        if self.status != DISCONNECTED:
            self.rpc('monitor.directory', directory)


    def register_file_type_attrs(self, name, **kwargs):
        """
        Register new attrs and types for files.
        """
        if self.status != DISCONNECTED:
            self.rpc('db.register_file_type_attrs', name, **kwargs)


    def register_track_type_attrs(self, name, **kwargs):
        """
        Register new attrs and types for files.
        """
        if self.status != DISCONNECTED:
            self.rpc('db.register_track_type_attrs', name, **kwargs)


    def delete_media(self, id):
        """
        Delete media with the given id.
        """
        if self.status != DISCONNECTED:
            self.rpc('db.media.delete', id)


    # -------------------------------------------------------------------------
    # Server connect / disconnect / reconnect handling
    # -------------------------------------------------------------------------

    def _connect(self):
        """
        Establish connection to the beacon server and locally connect to the
        database (if necessary).
        """
        if self.status != DISCONNECTED:
            # no re-connect needed
            return

        # monitor function from the server to start a new monitor for a query
        try:
            server = kaa.rpc.Client('beacon')
        except kaa.rpc.ConnectError, e:
            raise ConnectError(e)
        server.signals["closed"].connect_once(self._disconnected)
        server.connect(self)
        self.rpc = server.rpc
        self.status = CONNECTING


    def _disconnected(self):
        if self.status != CONNECTED:
            return
        log.info('disconnected from beacon server')
        kaa.notifier.WeakTimer(self._reconnect).start(2)
        self.status = DISCONNECTED
        self.signals['disconnect'].emit()


    def _reconnect(self):
        """
        See if the socket with the server is still alive, otherwise reconnect.
        """
        # Got disconnected; reconnect.
        try:
            self._connect()
        except ConnectError, e:
            # still dead
            return True

        # Reset monitors to queries
        for query in self._queries:
            if query != None and query.monitoring:
                self._beacon_monitor_add(query)

        return False


    def _shutdown(self):
        """
        Disconnect from the server.
        """
        self.status = SHUTDOWN
        for q in self._queries:
            if q != None:
                q.monitoring = False
        self._queries = []
        self.rpc = None
        self._db = None


    # -------------------------------------------------------------------------
    # Media Callback API
    # -------------------------------------------------------------------------

    def eject(self, dev):
        if self.rpc:
            return self.rpc('media.eject', dev.id)
        return False


    # -------------------------------------------------------------------------
    # Internal API
    # -------------------------------------------------------------------------

    def _beacon_monitor_add(self, query):
        """
        Monitor a query
        """
        if not self.status == CONNECTED:
            return
        q = copy.copy(query._query)
        if 'parent' in q:
            if not q['parent']._beacon_id:
                # we need the get the id first
                q['parent']._beacon_request(self._beacon_monitor_add, query)
                return
            q['parent'] = q['parent']._beacon_id
        self.rpc('monitor.add', self.id, query.id, q)


    def _beacon_monitor_remove(self, query):
        """
        Monitor a query
        """
        if not self.status == CONNECTED:
            return
        self.rpc('monitor.remove', self.id, query.id)


    def _beacon_request(self, filename, callback, *args, **kwargs):
        """
        Request information about a filename.
        """
        if not self.status == CONNECTED:
            return False
        self.rpc('item.request', filename).connect(callback, *args, **kwargs)
        return True


    def _beacon_query(self, **kwargs):
        """
        Do a query from the db.
        """
        self.rpc('db.lock')
        result = self._db.query(**kwargs)
        if isinstance(result, kaa.notifier.InProgress):
            cb = kaa.notifier.Callback(self.rpc, 'db.unlock')
            # Call args will be the result set of the query.  We don't want to
            # send this over RPC.
            cb.set_ignore_caller_args()
            result.connect(cb)
        else:
            self.rpc('db.unlock')
        return result


    def _beacon_update(self, item):
        """
        Update item in next main loop interation.
        """
        if not item._beacon_id:
            # item has no beacon id, request the data before
            # schedule the update
            item._beacon_request(self._beacon_update, item)
            return
        if not self._changed:
            # register timer to do the changes
            OneShotTimer(self._beacon_update_all).start(0.1)
        self._changed.append(item)


    def _beacon_update_all(self, item=None):
        """
        Update all items waiting.
        """
        if not self.status == CONNECTED:
            return
        # do the update now
        items = []
        for i in self._changed:
            # we have a valid item with id thanks to _beacon_update
            items.append((i._beacon_id, i._beacon_changes))
            i._beacon_changes = {}
        self._changed = []
        self.rpc('item.update', items)


    def _beacon_media_information(self, media):
        """
        Get some basic media information.
        (similar function in server)
        """
        self.rpc('db.lock')
        result = self._db.query_media(media)
        self.rpc('db.unlock')
        return result


    def _beacon_db_information(self):
        """
        Get some basic db information for debugging.
        """
        return self._db.get_db_info()


    # -------------------------------------------------------------------------
    # Server callbacks
    # -------------------------------------------------------------------------

    @kaa.rpc.expose('connect')
    def _connected(self, id, database, media):
        """
        Callback to pass the database information to the client.
        """
        # read only version of the database
        self._db = Database(database)
        # connect to server notifications
        self.id = id
        self.status = CONNECTED
        new_media = []
        medialist.connect(self)
        for id, prop in media:
            new_media.append(medialist.add(id, prop))
        self.signals['connect'].emit()
        # reconnect query monitors
        for query in self._queries[:]:
            if query == None:
                self._queries.remove(query)
                continue
            if query.monitoring:
                query.monitoring = False
                query.monitor(True)
        for m in new_media:
            if not m.mountpoint == '/':
                self.signals['media.add'].emit(m)


    @kaa.rpc.expose('notify')
    def notify(self, id, msg, *args):
        """
        Internal notification callback from the server. The Monitor does not
        has a reference to the Query because this would result in circular
        dependencies. So this function is needed to find the correct Query
        for a request.
        """
        for query in self._queries[:]:
            if query == None:
                self._queries.remove(query)
                continue
            if not query.id == id:
                continue
            if msg == 'progress':
                return query.signals['progress'].emit(*args)
            if msg == 'changed':
                return query._beacon_callback_changed(*args)
            if msg == 'checked':
                return query.signals['up-to-date'].emit()
            log.error('Error: unknown message from server: %s' % msg)
            return


    @kaa.rpc.expose('device.changed')
    def media_changed(self, id, prop):
        """
        Notification that the media with the given id changed.
        """
        if medialist.get_by_media_id(id):
            medialist.get_by_media_id(id).update(prop)
            return
        media = medialist.add(id, prop)
        self.signals['media.add'].emit(media)


    @kaa.rpc.expose('device.removed')
    def media_removed(self, id):
        """
        Notification that the media with the given id was removed.
        """
        media = medialist.remove(id)
        if media:
            self.signals['media.remove'].emit(media)
