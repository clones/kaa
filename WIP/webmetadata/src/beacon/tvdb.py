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
# Copyright (C) 2009 Dirk Meyer
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
import kaa.webmetadata.tvdb
import kaa.beacon

# relative beacon server imports
from ..parser import register as beacon_register

# get logging object
log = logging.getLogger('beacon.tvdb')

# tvdb object
tvdb = None

# beacon database object
beacondb = None

PLUGIN_VERSION = 0.2

def sync(entry, metadata):
    """
    Sync the data from tvdb.Filename entry to metadata
    """
    if entry.episode:
        if entry.episode.Overview:
            log.info('add description to %s', entry.filename)
            metadata['description'] = entry.episode.Overview
        if entry.episode.image:
            metadata['image'] = entry.episode.image
        if entry.series.data:
            metadata['tvdb_series'] = entry.series.data['name']
        try:
            if entry.episode.SeasonNumber:
                metadata['tvdb_season'] = int(entry.episode.SeasonNumber)
        except (ValueError, IndexError), e:
            pass
        try:
            if entry.episode.EpisodeNumber:
                metadata['tvdb_episode'] = int(entry.episode.EpisodeNumber)
        except (ValueError, IndexError), e:
            pass
        if entry.episode.name:
            metadata['tvdb_title'] = entry.episode.name


def parser(item, attributes, type):
    """
    Plugin for the beacon.parser
    """
    if type != 'video' or not item.filename:
        return
    entry = tvdb.from_filename(item.filename)
    if entry.alias:
        # store the alias and if we where sure this is a tv series
        attributes['tvdb_alias'] = entry.alias
        attributes['tvdb_sure'] = entry.sure
        if entry.series:
            # sync if it is a known series
            sync(entry, attributes)
            # FIXME: make sure we download the thumbnails

@kaa.coroutine()
def tvdb_populate():
    """
    Add tvdb metadata to beacon on first start
    """
    aliases = tvdb.aliases
    log.info('populate database with tvdb metadata')
    for item in (yield beacondb.query(type='video')):
        if not item.filename:
            continue
        entry = tvdb.from_filename(item.filename)
        # store the alias and if we where sure this is a tv series
        item['tvdb_alias'] = entry.alias
        item['tvdb_sure'] = entry.sure
        if entry.series:
            # sync if it is a known series
            sync(entry, item)
            # FIXME: make sure we download the thumbnails
    tvdb.set_metadata('beacon_init', PLUGIN_VERSION)
    tvdb.set_metadata('beacon_aliases', aliases)
    tvdb.set_metadata('beacon_timestamp', time.time())
    tvdb.set_metadata('beacon_version', tvdb.version)

@kaa.coroutine(kaa.POLICY_SYNCHRONIZED)
def tvdb_changed():
    """
    The tvdb database has changed, check against beacon
    """
    log.info('check TVDB changes')
    aliases = tvdb.aliases
    known = tvdb.get_metadata('beacon_aliases')
    timestamp = tvdb.get_metadata('beacon_timestamp') or 0
    tvdb.set_metadata('beacon_timestamp', time.time())
    tvdb.set_metadata('beacon_aliases', aliases)
    tvdb.set_metadata('beacon_version', tvdb.version)
    for alias in aliases:
        if not alias in known or timestamp < tvdb.get_series_by_alias(alias).timestamp:
            for item in (yield beacondb.query(type='video', tvdb_alias=alias)):
                entry = tvdb.from_filename(item.filename)
                sync(entry, item)


class Plugin:
    """
    This is class is used as a namespace and is exposed to beacon.
    """
    # plugin config object
    config = kaa.feedmanager.config

    @staticmethod
    def init(server, db):
        """
        Init the plugin.
        """
        kaa.beacon.register_file_type_attrs('video',
            tvdb_alias = (unicode, kaa.beacon.ATTR_SEARCHABLE),
            tvdb_sure = (bool, kaa.beacon.ATTR_SIMPLE),
            tvdb_series = (unicode, kaa.beacon.ATTR_SEARCHABLE),
            tvdb_season = (int, kaa.beacon.ATTR_SEARCHABLE),
            tvdb_episode = (int, kaa.beacon.ATTR_SEARCHABLE),
            tvdb_title = (unicode, kaa.beacon.ATTR_SIMPLE))
        global tvdb
        global beacondb
        beacondb = db
        beacon_register(None, parser)
        tvdb = kaa.webmetadata.tvdb.TVDB(db.directory + '/tvdb')
        tvdb.signals['changed'].connect(tvdb_changed)
        if tvdb.get_metadata('beacon_init') != PLUGIN_VERSION:
            # kaa.beacon does not know about this db, we need to create
            # the metadata for tvdb.
            tvdb_populate()
        elif tvdb.get_metadata('beacon_version') != tvdb.version:
            tvdb_changed()
