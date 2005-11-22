# -*- coding: iso-8859-1 -*-
# -----------------------------------------------------------------------------
# client.py - Client interface for the VFS
# -----------------------------------------------------------------------------
# $Id:$
#
# This is the client interface to the vfs. The server needs to be running.
# To use the server a Client object must be created. Once created, it is
# possible to start a query on the client.
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


# Python imports
import os
import logging

# kaa imports
from kaa.base import ipc, weakref
from kaa.notifier import OneShotTimer

# kaa.vfs imports
from db import Database
from query import Query

# get logging object
log = logging.getLogger('vfs')


class Client(object):
    """
    VFS Client. This client uses the db read only and needs a server on
    the same machine doing the file scanning and changing of the db.
    """
    def __init__(self, db):
        # monitor function from the server to start a new monitor for a query
        self._server = ipc.IPCClient('vfs').get_object('vfs')(db)
        self.monitor = self._server.monitor
        # read only version of the database
        self.database = Database(db)
        self.database.read_only = True
        # connect to server notifications
        self._server.connect(self)
        # internal list of active queries
        self._queries = []


    def add_mountpoint(self, device, directory):
        """
        Add a mountpoint to the system.
        """
        self._server.add_mountpoint(device, directory)


    def query(self, **query):
        """
        Do a query to the databse. This will return a Query object.
        """
        # make sure filename in a query are normalized
        if 'dirname' in query:
            query['dirname'] = os.path.normpath(os.path.abspath(query['dirname']))
        if 'files' in query:
            query['files'] = [ os.path.normpath(os.path.abspath(x)) \
                               for x in query['files'] ]
        # TODO: reuse Query with same 'query'
        result = Query(self, query)
        self._queries.append(weakref(result))

        # start the remote query 100 ms seconds later. It is faster
        # that way because a) ipc takes some time and b) it avoids
        # doing the same stuff at the same time

        # TODO: create a client id to avoid sending self.notify to the
        # client at this point.
        OneShotTimer(self.monitor, self.notify, result.id,
                     __ipc_oneway=True, **query).start(0.1)
        return result


    def notify(self, id, msg, *args, **kwargs):
        """
        Internal notification callback from the server. The Monitor does not
        has a reference to the Query because this would result in circular
        dependencies. So this function is needed to find the correct Query
        for a request.
        """
        for query in self._queries:
            if query and query.id == id:
                if hasattr(query, '_vfs_%s' % msg):
                    getattr(query, '_vfs_%s' % msg)(*args, **kwargs)
                    return
                
                log.error('Error: unknown message from server: %s' % msg)
                return
            
        # not found, possibly already deleted, check for dead weakrefs
        for query in self._queries[:]:
            if not query:
                self._queries.remove(query)


    def __str__(self):
        """
        Convert object to string (usefull for debugging)
        """
        return '<vfs.Client>'
