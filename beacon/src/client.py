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


# Python imports
import os
import copy
import logging

# kaa imports
import kaa
import kaa.rpc
from kaa.weakref import weakref
from kaa.notifier import OneShotTimer, Signal

# kaa.beacon imports
from db import Database
from query import Query

# get logging object
log = logging.getLogger('beacon')

DISCONNECTED = 'disconnected'
CONNECTING   = 'connecting'
CONNECTED    = 'connected'
SHUTDOWN     = 'shutdown'

class Client(object):
    """
    Beacon client. This client uses the db read only and needs a server on
    the same machine doing the file scanning and changing of the db.
    """
    def __init__(self):
        self.database = None

        self.signals = {
            'connect'   : Signal(),
            'disconnect': Signal()
        }

        # internal list of active queries
        self._queries = []
        # internal list of items to update
        self._changed = []
        # add ourself to shutdown handler for correct disconnect
        kaa.signals['shutdown'].connect(self._shutdown)
        self.status = DISCONNECTED
        self._connect()


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
        log.info('connecting')
        server = kaa.rpc.Client('beacon')
        server.signals["closed"].connect_once(self._disconnected)
        server.connect(self)
        self.rpc = server.rpc
        self.status = CONNECTING


    def _disconnected(self):
        if self.status != CONNECTED:
            return
        log.warning('disconnected from beacon server')
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
        except Exception, e:
            # still dead
            return True

        # reset monitors to queries
        for query in self._queries:
            if query != None and query.monitoring:
                self._beacon_monitor_add(query)

        # FIXME: also set up all information in the database again, like
        # mountpoints and directories to monitor
        log.info('beacon connected again')
        return False


    def _shutdown(self):
        """
        Disconnect from the server.
        """
        self.status = SHUTDOWN
        for q in self._queries:
            if q:
                q.monitoring = False
        self._queries = []
        self.rpc = None
        self.database = None


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
            q['parent'] = q['parent']._beacon_id
        self.rpc('monitor.add')(self.id, query.id, q)


    def _beacon_monitor_remove(self, query):
        """
        Monitor a query
        """
        if not self.status == CONNECTED:
            return
        self.rpc('monitor.remove')(self.id, query.id)


    def _beacon_request(self, filename, callback, *args, **kwargs):
        """
        Request information about a filename.
        """
        if not self.status == CONNECTED:
            return False
        self.rpc('item.request', callback, *args, **kwargs)(filename)
        return True


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
            id = i._beacon_id
            if not id:
                # FIXME: How to update an item not in the db? Right now we
                # can't do that and will drop the item.
                continue
            items.append((id, i._beacon_changes))
            i._beacon_changes = {}
        self._changed = []
        self.rpc('item.update')(items)


    def __repr__(self):
        """
        Convert object to string (usefull for debugging)
        """
        return '<beacon.Client>'


    # -------------------------------------------------------------------------
    # Server callbacks
    # -------------------------------------------------------------------------

    @kaa.rpc.expose('connect')
    def _connected(self, id, database, mountpoints):
        # read only version of the database
        self.database = Database(database, self)
        # connect to server notifications
        self.id = id
        self.status = CONNECTED
        for type, device, directory, name in mountpoints:
            self.database.add_mountpoint(type, device, directory)
            self.database.set_mountpoint(directory, name)
        self.signals['connect'].emit()
        # reconnect query monitors
        for query in self._queries[:]:
            if query == None:
                self._queries.remove(query)
                continue
            if query.monitoring:
                query.monitoring = False
                query.monitor(True)


    @kaa.rpc.expose('notify')
    def notify(self, id, msg, *args, **kwargs):
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
            callback = getattr(query, '_beacon_callback_%s' % msg, None)
            if callback:
                return callback(*args, **kwargs)
            log.error('Error: unknown message from server: %s' % msg)
            return
