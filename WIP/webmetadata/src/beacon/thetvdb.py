# -*- coding: iso-8859-1 -*-
# -----------------------------------------------------------------------------
# tvdb.py - TVDB Beacon Plugin
# -----------------------------------------------------------------------------
# $Id$
#
# This file provides a bridge between the tvdb and Beacon.
# It will be installed in the kaa.beacon tree
#
# -----------------------------------------------------------------------------
# kaa.webmetadata - Receive Metadata from the Web
# Copyright (C) 2009,2011 Dirk Meyer
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
import logging
import time

# kaa imports
import kaa
import kaa.webmetadata
import kaa.beacon

# relative beacon server imports
from ..parser import register as beacon_register

# get logging object
log = logging.getLogger('beacon.tvdb')

# beacon database object
beacondb = None

PLUGIN_VERSION = 0.3

def sync((series, episode), metadata):
    """
    Sync the data from tvdb.Filename entry to metadata
    """
    if episode.Overview:
        metadata['description'] = episode.Overview
    if episode.image:
        metadata['image'] = episode.image
    if series.data:
        metadata['series'] = series.data['name']
    if episode.name:
        metadata['title'] = episode.name


def parser(item, attributes, type):
    """
    Plugin for the beacon.parser
    """
    if type != 'video' or not item.filename:
        return
    if attributes.get('season') and attributes.get('episode') and attributes.get('show'):
        result = kaa.webmetadata.parse('thetvdb:%s' % item.get('series'))
        if result:
            parser, series = result
            episode = series.get_season(item.get('season')).get_episode(item.get('episode'))
            sync((series, episode), attributes)


@kaa.coroutine(kaa.POLICY_SYNCHRONIZED)
def tvdb_resync():
    """
    The tvdb database has changed, check against beacon
    """
    log.info('check TVDB changes')
    for item in (yield beacondb.query(type='video')):
        if item.get('series') and item.get('season') and item.get('episode'):
            result = kaa.webmetadata.parse('thetvdb:%s' % item.get('series'))
            if result:
                parser, series = result
                episode = series.get_season(item.get('season')).get_episode(item.get('episode'))
                sync((series, episode), item)
    kaa.webmetadata.set_metadata('thetvdb:beacon_init', PLUGIN_VERSION)
    kaa.webmetadata.set_metadata('thetvdb:beacon_timestamp', time.time())
    kaa.webmetadata.set_metadata('thetvdb:beacon_version', kaa.webmetadata.backends['thetvdb'].version)

class Plugin:
    """
    This is class is used as a namespace and is exposed to beacon.
    """

    @staticmethod
    def init(server, db):
        """
        Init the plugin.
        """
        kaa.webmetadata.init(base=db.directory)
        global beacondb
        beacondb = db
        beacon_register(None, parser)
        kaa.webmetadata.backends['thetvdb'].signals['changed'].connect(tvdb_resync)
        if kaa.webmetadata.get_metadata('thetvdb:beacon_init') != PLUGIN_VERSION:
            # kaa.beacon does not know about this db, we need to create
            # the metadata for tvdb.
            tvdb_resync()
        elif kaa.webmetadata.get_metadata('thetvdb:beacon_version') != \
                kaa.webmetadata.backends['thetvdb'].version:
            tvdb_resync()
