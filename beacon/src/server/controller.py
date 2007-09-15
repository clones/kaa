# -*- coding: iso-8859-1 -*-
# -----------------------------------------------------------------------------
# controller.py - Server controller interface for Media and Item
# -----------------------------------------------------------------------------
# $Id$
#
# -----------------------------------------------------------------------------
# kaa.beacon.server - A virtual filesystem with metadata
# Copyright (C) 2007 Dirk Meyer
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

__all__ = [ 'Controller' ]

# kaa imports
import kaa.notifier

# kaa.beacon imports
import hwmon
from kaa.beacon.media import medialist
from parser import parse


class Controller(object):
    """
    The controller defines the callbacks Item and Media need. On client
    side this is all implemented in the Client class.
    """
    def __init__(self, handler, db, rootfs=None):
        self._db = db
        self._changed = []
        hwmon.connect()
        medialist.connect(self)
        hwmon.set_database(handler, db, rootfs)

    # Item callbacks

    def _beacon_parse(self, item):
        """
        Parse an item
        """
        return parse(self._db, item)


    @kaa.notifier.yield_execution()
    def _beacon_update_all(self):
        """
        Timed callback to write all changes to the db.
        """
        while self._db.read_lock.is_locked():
            yield self._db.read_lock.yield_unlock()
        changes = self._changed
        self._changed = []
        for item in changes:
            self._db.update_object(item._beacon_id, item._beacon_changes)
            item._beacon_changes = {}
        # commit to update monitors
        self._db.commit()


    def _beacon_update(self, item):
        """
        Mark item as changed to be updated in the db.
        """
        if not self._changed:
            # register timer to do the changes
            kaa.notifier.OneShotTimer(self._beacon_update_all).start(0.1)
        self._changed.append(item)


    def query(self, **query):
        """
        Database query.
        """
        return self._db.query(**query)


    @kaa.notifier.yield_execution()
    def delete_item(self, item):
        """
        Delete an item.
        """
        while self._db.read_lock.is_locked():
            yield self._db.read_lock.yield_unlock()
        self._db.delete_object(item._beacon_id)

    # Media callbacks

    def eject(self, media):
        """
        Eject media
        """
        hwmon.get_client().eject(media)


    def _beacon_media_information(self, media):
        """
        Get media information from te database.
        """
        return self._db.query_media(media)
