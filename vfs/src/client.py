# -*- coding: iso-8859-1 -*-
# -----------------------------------------------------------------------------
# client.py - Client interface for the VFS
# -----------------------------------------------------------------------------
# $Id: device.py 799 2005-09-16 14:27:36Z rshortt $
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


from kaa.base import ipc, weakref
from kaa.notifier import Signal, OneShotTimer
import os

from db import Database

class Query(object):
    def __init__(self, client, query):
        self.signals = { 'changed': Signal(), 'progress': Signal(),
                         'up-to-date': Signal() }
        if 'dirname' in query:
            query['dirname'] = os.path.normpath(os.path.abspath(query['dirname']))
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
        # FIXME: make sure the monitor has the same results from the
        # database as the client side and case there are no updates
        self._monitor = monitor
        self.id = id

    def _handle_db_return(self):

        # transform result
        result = self._result_t
        self._result_t = None
        result = result.get()

        if self._result == None:
            self._result = result
            return
        changed = False
        if not result or not hasattr(result[0], 'url'):
            # normal string results
            if result != self._result:
                self._result = result
                self.signals['changed'].emit()
            self.signals['up-to-date'].emit()
            return

        for pos, item in enumerate(result):
            if not len(self._result) > pos:
                self._result.append(item)
                changed = True
                continue
            current = self._result[pos]
            while current and item.url > current.url:
                self._result.remove(current)
                if len(self._result) > pos:
                    current = self._result[pos]
                else:
                    current = None
                changed = True
            if current and item.url == current.url:
                if current.data['mtime'] != item.data['mtime']:
                    changed = True
                    current.data = item.data
                continue
            self._result.insert(pos, item)
        if len(self._result) > pos + 1:
            changed = True
            self._result = self._result[:pos+1]
        if changed:
            self.signals['changed'].emit()
        self.signals['up-to-date'].emit()

    def get(self):
        if self._result_t:
            self._handle_db_return()
        return self._result[:]

    def notify(self, msg, *args, **kwargs):
        if msg == 'changed':
            # do not believe this, wait for up-to-date and check again
            pass
        elif msg == 'up-to-date':
            self._result_t = self._client.database.query(**self._query)
            self._result_t.connect(self._handle_db_return)
        else:
            self.signals[msg].emit(*args)

    def __str__(self):
        return '<Client.Query for %s>' % self._query


class Client(object):
    def __init__(self, db):
        self._server = ipc.IPCClient('vfs').get_object('vfs')(db)
        self.monitor = self._server.monitor
        self.database = Database(db)
        self.database.read_only = True
        self._queries = []

    def query(self, **query):
        #print 'start query'
        query = Query(self, query)
        # TODO: clean up dead weakrefs later
        self._queries.append(weakref(query))
        return query

    def notify(self, id, *args, **kwargs):
        for query in self._queries:
            if query and query.id == id:
                query.notify(*args, **kwargs)
                return
        print 'Error: not found'
