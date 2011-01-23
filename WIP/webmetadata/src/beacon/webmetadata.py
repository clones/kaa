# -*- coding: iso-8859-1 -*-
# -----------------------------------------------------------------------------
# webmetadata.py - Webmetadata Plugin
# -----------------------------------------------------------------------------
# $Id: tvdb.py 4205 2009-07-19 11:20:16Z dmeyer $
#
# This file provides a bridge between the kaa.webmetadata and Beacon.
# It will be installed in the kaa.beacon tree
#
# -----------------------------------------------------------------------------
# kaa.webmetadata - Receive Metadata from the Web
# Copyright (C) 2010-2011 Dirk Meyer
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

# kaa imports
import kaa
import kaa.webmetadata
import kaa.beacon

# relative beacon server imports
from ..parser import register as beacon_register

# get logging object
log = logging.getLogger('beacon.webmetadata')

PLUGIN_VERSION = 0.1


class Plugin:
    """
    This is class is used as a namespace and is exposed to beacon.
    """

    # beacon database object
    beacondb = None
    todo = []

    @kaa.coroutine(policy=kaa.POLICY_SYNCHRONIZED)
    def guess(self, item):
        """
        Guess some metadata for the item
        """
        if kaa.webmetadata.parse(item.filename):
            log.info('skip %s' % item.filename)
            self.parser(item, None, 'video')
            yield None
        log.info('guess %s' % item.filename)
        try:
            result = yield kaa.webmetadata.search(item.filename)
            if len(result) == 1:
                log.info('found match for %s' % (item.get('series') or item.filename))
                if not (yield kaa.webmetadata.match(item.filename, result[0].id)):
                    log.error('matching error ... what to do now?')
                    yield None
                if not item.get('series'):
                    # tv series get an auto sync due to db version
                    # change. For movies we need to parse again.
                    self.parser(item, None, 'video')
                yield None
        except Exception, e:
            log.exception('kaa.webmetadata error')
        log.info('failed guessing %s' % (item.get('series') or item.filename))
        self.failed.append(item.get('series') or item.filename)
        kaa.webmetadata.set_metadata('beacon_failed', self.failed)

    def parser(self, item, attributes, type):
        """
        Plugin for the beacon.parser
        """
        if type != 'video' or not item.filename:
            return None
        metadata = kaa.webmetadata.parse(item.filename, attributes)
        if not attributes:
            attributes = item
        if metadata:
            attributes['title'] = metadata.title
            attributes['description'] = metadata.overview
            if isinstance(metadata, kaa.webmetadata.Episode):
                attributes['series'] = metadata.series.title
                attributes['image'] = metadata.image
            if isinstance(metadata, kaa.webmetadata.Movie):
                if metadata.posters:
                    attributes['image'] = metadata.posters[0].url
            return None
        if attributes.get('series') and attributes.get('series') not in self.failed:
            self.guess(item)
        else:
            nfo = os.path.splitext(item.filename)[0] + '.nfo'
            if os.path.exists(nfo):
                self.guess(item)
        return None

    @kaa.coroutine(policy=kaa.POLICY_SYNCHRONIZED)
    def resync(self, force, series_only=False):
        """
        The database has changed, check against beacon
        """
        log.info('check web metadata changes')
        if force:
            self.todo = []
            self.failed = []
            for item in (yield self.beacondb.query(type='video')):
                if not item.filename:
                    continue
                if item.filename and \
                        (not series_only or \
                             (item.get('series') and item.get('season') and item.get('episode'))):
                    self.todo.append(item._beacon_id[1])
            kaa.webmetadata.set_metadata('beacon_todo', self.todo)
            kaa.webmetadata.set_metadata('beacon_failed', [])
        else:
            self.todo = kaa.webmetadata.get_metadata('beacon_todo')
            self.failed = kaa.webmetadata.get_metadata('beacon_failed')
        kaa.webmetadata.set_metadata('beacon_init', PLUGIN_VERSION)
        kaa.webmetadata.set_metadata('beacon_version', kaa.webmetadata.db_version())
        yield kaa.delay(2)
        while self.todo:
            items = yield self.beacondb.query(type='video', id=self.todo.pop(0))
            if items:
                self.parser(items[0], None, 'video')
            kaa.webmetadata.set_metadata('beacon_todo', self.todo)

    @staticmethod
    def init(server, db):
        """
        Init the plugin.
        """
        plugin = Plugin()
        plugin.beacondb = db
        kaa.webmetadata.init(base=db.directory)
        kaa.webmetadata.backends['thetvdb'].signals['changed'].connect(plugin.resync, True, True)
        beacon_register(None, plugin.parser)
        if kaa.webmetadata.get_metadata('beacon_init') != PLUGIN_VERSION:
            # kaa.beacon does not know about this db, we need to create
            # the metadata for themoviedb.
            log.info('populate database with web metadata')
            plugin.resync(force=True)
        else:
            plugin.resync(force=False)
