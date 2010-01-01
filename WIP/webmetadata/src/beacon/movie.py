# -*- coding: iso-8859-1 -*-
# -----------------------------------------------------------------------------
# themoviedb.py - The MovieDB Plugin
# -----------------------------------------------------------------------------
# $Id: tvdb.py 4205 2009-07-19 11:20:16Z dmeyer $
#
# This file provides a bridge between the themoviedb and Beacon.
# It will be installed in the kaa.beacon tree
#
# -----------------------------------------------------------------------------
# kaa.webmetadata - Receive Metadata from the Web
# Copyright (C) 2010 Dirk Meyer
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

# python imports
import os
import logging
import time

# kaa imports
import kaa
import kaa.webmetadata
import kaa.webmetadata.themoviedb
import kaa.beacon

# relative beacon server imports
from ..parser import register as beacon_register

# get logging object
log = logging.getLogger('beacon.themoviedb')

PLUGIN_VERSION = 0.02

processed = {}

class Plugin:
    """
    This is class is used as a namespace and is exposed to beacon.
    """

    # themoviedb object
    themoviedb = None

    # beacon database object
    beacondb = None

    @kaa.coroutine()
    def parser(self, item, attributes, type):
        """
        Plugin for the beacon.parser
        """
        if type != 'video' or not item.filename:
            yield None
        nfo = os.path.splitext(item.filename)[0] + '.nfo'
        if not os.path.exists(nfo):
            yield None
        entry = self.themoviedb.from_filename(item.filename)
        if entry.available:
            attributes['title'] = entry.title
            attributes['description'] = entry.plot
            # FIXME: let the user choose?
            if entry.images:
                attributes['image'] = entry.images[0].url
            # FIXME: we need a way to notify a watching beacon client
            # that this item has changed. No idea how we can do this
            # in a plugin.
            yield None
        if item._beacon_id in processed:
            failed = self.themoviedb.get_metadata('beacon_failed') or []
            self.themoviedb.set_metadata('beacon_failed', failed)
            yield None
        yield entry.fetch()
        # FIXME: processed is an ugly variable to avoid fetching
        # an item that cannot be fetched over and over again. We
        # will retry on the next startup since this variable is
        # not cached. This is ugly
        processed[item._beacon_id] = True
        yield self.parser(item, attributes, type)

    @staticmethod
    @kaa.coroutine()
    def init(server, db):
        """
        Init the plugin.
        """
        plugin = Plugin()
        plugin.beacondb = db
        beacon_register(None, plugin.parser)
        plugin.themoviedb = kaa.webmetadata.themoviedb.MovieDB(db.directory + '/themoviedb')
        if plugin.themoviedb.get_metadata('beacon_init') != PLUGIN_VERSION + 1:
            # kaa.beacon does not know about this db, we need to create
            # the metadata for themoviedb.
            log.info('populate database with themoviedb metadata')
            todo = []
            for item in (yield plugin.beacondb.query(type='video')):
                if not item.filename:
                    continue
                todo.append(item._beacon_id[1])
            plugin.themoviedb.set_metadata('beacon_init', PLUGIN_VERSION + 3)
            plugin.themoviedb.set_metadata('beacon_todo', todo)
            plugin.themoviedb.set_metadata('beacon_timestamp', time.time())
        todo = plugin.themoviedb.get_metadata('beacon_todo')
        failed = plugin.themoviedb.get_metadata('beacon_failed') or []
        todo = todo + failed
        while todo:
            items = yield plugin.beacondb.query(type='video', id=todo.pop(0))
            if items:
                yield plugin.parser(items[0], items[0], 'video')
            plugin.themoviedb.set_metadata('beacon_todo', todo)
