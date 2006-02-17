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

    def __init__(self, client, **query):
        self.signals = {
            'changed': Signal(),
            'progress': Signal(),
            'up-to-date': Signal()
            }
        self.id = Query.NEXT_ID
        Query.NEXT_ID += 1
        self._query = query
        self._monitor = False
        self._client = client

        self.result = self._client.database.query(**query)
    

    def monitor(self, status=True):
        """
        Turn on/off query mnitoring
        """
        if self._monitor == status:
            return
        self._client.monitor(self, status)
        self._monitor = status

        
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
        self.signals['up-to-date'].emit()
        return


    def _vfs_updated(self, items):
        """
        Checked message from server.
        """
#         print 'UPDATE'
        url, data = items.pop(0)
        for r in self.result:
            if r.url == url:
                r._vfs_database_update(data)
                if not items:
                    break
                url, data = items.pop(0)
        if items:
            log.error('not all items found')


    def _vfs_changed(self):
        self.result = self._client.database.query(**self._query)
        self.signals['changed'].emit()

        
    def __repr__(self):
        """
        Convert object to string (usefull for debugging)
        """
        return '<vfs.Client.Query for %s>' % self._query


    def __del__(self):
        """
        Memory debug
        """
        print 'del', repr(self)


    def __iter__(self):
        return self.result.__iter__()
