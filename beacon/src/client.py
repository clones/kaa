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
# TODO: make it possible to update an item that is not in the database.
#
# -----------------------------------------------------------------------------
# kaa-beacon - A virtual filesystem with metadata
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


# Python imports
import os
import copy
import logging

# kaa imports
import kaa
import kaa.ipc
from kaa.weakref import weakref
from kaa.notifier import OneShotTimer

# kaa.beacon imports
from db import Database
from query import Query

# get logging object
log = logging.getLogger('beacon')


class Client(object):
    """
    Beacon client. This client uses the db read only and needs a server on
    the same machine doing the file scanning and changing of the db.
    """
    def __init__(self):
        self.database = None

        self._connect()
        # internal list of active queries
        self._queries = []
        # internal list of items to update
        self._changed = []
        # add ourself to shutdown handler for correct disconnect
        kaa.signals['shutdown'].connect(self.disconnect)
        kaa.notifier.WeakTimer(self._check_is_connected).start(5)


    def _connect(self):
        """
        Establish connection to the beacon server and locally connect to the
        database (if necessary).
        """
        # monitor function from the server to start a new monitor for a query
        self._server = kaa.ipc.IPCClient('beacon').get_object('beacon')
        self._monitor = self._server.monitor
        # read only version of the database
        if not self.database:
            self.database = Database(self._server.get_database(), self)
        # connect to server notifications
        self.id = self._server.connect(self)

    def _check_is_connected(self):
        """
        See if the socket with the server is still alive, otherwise reconnect.
        """
        if kaa.ipc.is_proxy_alive(self._server):
            # Still alive.
            return True

        # Got disconnected; reconnect.
        try:
            self._connect()
        except kaa.ipc.IPCSocketError, (err, msg):
            log.error('Error: failed to connect to beacon server: %s (errno=%d)' % (msg, err))

        # FIXME: re-register any monitors with the server that may have been
        # lost due to a disconnect.  dischi? :)


    def disconnect(self):
        """
        Disconnect from the server.
        """
        for q in self._queries:
            if q:
                q._monitor = False
        self._queries = []
        self._server = None
        self._monitor = None
        self.database = None
        
        
    def add_mountpoint(self, device, directory):
        """
        Add a mountpoint to the system.
        """
        self._server.add_mountpoint(device, directory)


    def get(self, filename):
        """
        Return an object for the given filename.
        """
        filename = os.path.realpath(filename)
        result = Query(self, filename=filename).result
        return result


    def query(self, **query):
        result = Query(self, **query)
        self._queries.append(weakref(result))
        return result
    

    def monitor(self, query, status):
        """
        Monitor a query
        """
        q = None
        if status:
            q = copy.copy(query._query)
            if 'parent' in q:
                q['parent'] = q['parent']._beacon_id

        self._check_is_connected()
        self._monitor(self.id, query.id, q, __ipc_noproxy_args=True, __ipc_oneway=True)
        

    def _beacon_request(self, filename):
        """
        Request information about a filename.
        """
        return self._server.request(filename, __ipc_noproxy_result=True,
                                    __ipc_noproxy_args=True)


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
            if query.id == id:
                if hasattr(query, '_beacon_%s' % msg):
                    getattr(query, '_beacon_%s' % msg)(*args, **kwargs)
                    return
                
                log.error('Error: unknown message from server: %s' % msg)
                return


    def update(self, item=None):
        """
        Update item in next main loop interation.
        """
        if not item:
            # do the update now
            items = []
            for i in self._changed:
                id = i._beacon_id
                if not id:
                    # TODO: How to update an item not in the db? Right now we
                    # can't do that and will drop the item.
                    continue
                items.append((id, i._beacon_changes))
                i._beacon_changes = {}
            self._changed = []
            self._server.update(items, __ipc_oneway=True, __ipc_noproxy_args=True)
            return

        if not self._changed:
            # register timer to do the changes
            OneShotTimer(self.update).start(0.1)
        self._changed.append(item)

        
    def __repr__(self):
        """
        Convert object to string (usefull for debugging)
        """
        return '<beacon.Client>'


    def __del__(self):
        """
        Debug in __del__.
        """
        return 'del', self
