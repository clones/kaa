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
from kaa.notifier import OneShotTimer, Signal

# kaa.beacon imports
from db import Database
from query import Query

# get logging object
log = logging.getLogger('beacon')

DISCONNECTED = 'disconnected'
CONNECTED    = 'connected'
SHUTDOWN     = 'shutdown'

class ServerIPC(object):
    def __init__(self):
        self.connection = kaa.ipc.IPCClient('beacon')
        self.signals = self.connection.signals
        self.server = self.connection.get_object('beacon')
        self.monitor = self.server.monitor

    def __getattr__(self, attr):
        return getattr(self.server, attr)

    def is_alive(self):
        return kaa.ipc.is_proxy_alive(self.server)
        
class Client(object):
    """
    Beacon client. This client uses the db read only and needs a server on
    the same machine doing the file scanning and changing of the db.
    """
    def __init__(self):
        self.database = None

        self.signals = {
            'connect': Signal(),
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


    def _connect(self):
        """
        Establish connection to the beacon server and locally connect to the
        database (if necessary).
        """
        if self.status != DISCONNECTED:
            # no re-connect needed
            return

        # monitor function from the server to start a new monitor for a query
        self._server = ServerIPC()
        self._server.signals["closed"].connect_once(self._disconnected)
        # read only version of the database
        if not self.database:
            self.database = Database(self._server.get_database(), self)
        # connect to server notifications
        self.id = self._server.connect(self)
        self.status = CONNECTED
        self.signals['connect'].emit()


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
        if self._server.is_alive():
            # already alive again
            return False

        # Got disconnected; reconnect.
        try:
            self._connect()
        except kaa.ipc.IPCSocketError, (err, msg):
            # still dead
            return True

        # reset monitors to queries
        for query in self._queries:
            if query != None and query.monitoring:
                self.monitor_query(query, True)

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
        self._server = None
        self.database = None
        
        
    def add_mountpoint(self, device, directory):
        """
        Add a mountpoint to the system.
        """
        if not self.status == CONNECTED:
            return
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
    

    def monitor_query(self, query, status):
        """
        Monitor a query
        """
        if not self.status == CONNECTED:
            return
        q = None
        if status:
            q = copy.copy(query._query)
            if 'parent' in q:
                q['parent'] = q['parent']._beacon_id

        self._server.monitor(self.id, query.id, q, __ipc_noproxy_args=True,
                             __ipc_oneway=True)
        

    def _beacon_request(self, filename):
        """
        Request information about a filename.
        """
        if not self.status == CONNECTED:
            return None
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
        if not self.status == CONNECTED:
            return
        if not item:
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
