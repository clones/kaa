# -*- coding: iso-8859-1 -*-
# -----------------------------------------------------------------------------
# query.py - Query class for the client
# -----------------------------------------------------------------------------
# $Id$
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
import logging

# kaa imports
from kaa.notifier import Signal

# get logging object
log = logging.getLogger('vfs')


class Query(object):
    """
    Query object for the client. Created by Client.query()
    """
    NEXT_ID = 1

    def __init__(self, client, query):
        self.signals = {
            'changed': Signal(),
            'progress': Signal(),
            'up-to-date': Signal()
            }
        self.id = Query.NEXT_ID
        Query.NEXT_ID += 1
        self._query = query
        self._monitor = None
        self._client = client
        self._result = self._client.database.query(**query)

    def get(self):
        """
        Get the result of the query.
        """
        if self._query.has_key('device'):
            return self._result
        return self._result[:]


    def _vfs_connect(self, monitor):
        """
        Connect message from server.
        """
        self._monitor = monitor


    def _vfs_progress(self, pos, max, url):
        """
        Progress message from server.
        """
        self.signals['progress'].emit(pos, max, url)
        return


    def _vfs_checked(self):
        """
        Checked message from server.
        """
        # The server checked the query, we should redo the query
        # to get possible updates.
        result = self._client.database.query(**self._query)
        log.info('check db results against current list of items')
        
        if self._query.has_key('device'):
            self._result = result
            self.signals['changed'].emit()
            return
        
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


    def __str__(self):
        """
        Convert object to string (usefull for debugging)
        """
        return '<vfs.Client.Query for %s>' % self._query

