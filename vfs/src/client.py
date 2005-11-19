# -*- coding: iso-8859-1 -*-
# -----------------------------------------------------------------------------
# client.py - Client interface for the VFS
# -----------------------------------------------------------------------------
# $Id: device.py 799 2005-09-16 14:27:36Z rshortt $
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
from kaa.notifier import Signal, OneShotTimer

# kaa.vfs imports
from db import Database
import item

# get logging object
log = logging.getLogger('vfs')

# ipc debugging
# ipc.DEBUG = 1

class Query(object):
    """
    Query object for the client. Created by Client.query()
    """
    def __init__(self, client, query):
        self.signals = {
            'changed': Signal(),
            'progress': Signal(),
            'up-to-date': Signal()
            }
        self.id = 0
        self._query = query
        self._monitor = None
        self._client = client
        self._result = None
        self._result_t = self._client.database.query(**query)

        # start the remote query 100 ms seconds later. It is faster
        # that way because a) ipc takes some time and b) it avoids
        # doing the same stuff at the same time
        OneShotTimer(self._client.monitor, self._client.notify,
                     __ipc_async=self._get_monitor, **query).start(0.1)


    def _get_monitor(self, (monitor, id)):
        """
        Callback to get a remote object (monitor) from the server. The
        object is used to identify the query on notifications and keep
        monitoring alive. If this objects dies, the monitor also dies.
        """
        self._monitor = monitor
        self.id = id


    def _handle_db_return(self):
        """
        Parse the results from the database query. Do not just replace the
        objects, only replace the internal data to keep old objects used
        by the application valid. Send signals on changes and send up-to-date
        signal.
        """
        if not self._result_t:
            # Maybe this could happen due to bad timing. Better save than
            # sorry.
            return

        # transform result
        result = self._result_t
        self._result_t = None
        result = result.get()

        if self._result == None:
            # First time this function is called
            if result and isinstance(result[0], item.Item):
                for r in result:
                    # change the internal db of the item to out client
                    r.db = self._client
            self._result = result
            return

        log.info('check db results against current list of items')

        changed = False
        if not result or not hasattr(result[0], 'url'):
            # normal string results
            if result != self._result:
                self._result = result
                self.signals['changed'].emit()
            self.signals['up-to-date'].emit()
            return

        # check old and new item lists. Both lists are sorted, so
        # checking can be done with simple cmp of the urls.
        for pos, dbitem in enumerate(result):
            if not len(self._result) > pos:
                # change the internal db of the item to out client
                dbitem.db = self._client
                self._result.append(dbitem)
                changed = True
                continue
            current = self._result[pos]
            while current and dbitem.url > current.url:
                self._result.remove(current)
                if len(self._result) > pos:
                    current = self._result[pos]
                else:
                    current = None
                changed = True
            if current and dbitem.url == current.url:
                if current.data['mtime'] != dbitem.data['mtime'] or \
                   current.dbid != dbitem.dbid:
                    changed = True
                    current.data = dbitem.data
                    current.dbid = dbitem.dbid
                # TODO: this is not 100% correct. Maybe the parent changed, or
                # the parent of the parent and we have now a new cover
                current.parent = dbitem.parent
                continue
            # change the internal db of the item to out client
            dbitem.db = self._client
            changed = True
            self._result.insert(pos, dbitem)

        if len(self._result) > pos + 1:
            changed = True
            self._result = self._result[:pos+1]

        if changed:
            # send changed signal
            log.debug('db has changed for %s, send signal %s'\
                      % (self._query, self.signals['changed']._callbacks))
            self.signals['changed'].emit()
        # send up-to-date signal
        self.signals['up-to-date'].emit()


    def get(self):
        """
        Get the result of the query. This could result in waiting for
        the db to finish using notifier.step().
        """
        if self._result_t:
            self._handle_db_return()
        if self._query.has_key('device'):
            if self._result:
                return self._result[0]
            else:
                return None
        return self._result[:]


    def notify(self, msg, *args, **kwargs):
        """
        Notifications from the server (callback).
        """
        if msg == 'checked':
            # The server checked the query, we should redo the query
            # to get possible updates.
            self._result_t = self._client.database.query(**self._query)
            self._result_t.connect(self._handle_db_return)
            return
        if msg == 'progress':
            # progress update when scanning
            self.signals[msg].emit(*args)
            return
        log.error('Error: unknown message from server: %s' % msg)


    def __str__(self):
        """
        Convert object to string (usefull for debugging)
        """
        return '<vfs.Client.Query for %s>' % self._query



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
        self._server.add_mountpoint(device, directory, __ipc_oneway=True)


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
        query = Query(self, query)
        self._queries.append(weakref(query))
        return query


    def notify(self, id, *args, **kwargs):
        """
        Internal notification callback from the server. The Monitor does not
        has a reference to the Query because this would result in circular
        dependencies. So this function is needed to find the correct Query
        for a request.
        """
        for query in self._queries:
            if query and query.id == id:
                query.notify(*args, **kwargs)
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
