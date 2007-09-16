# -*- coding: iso-8859-1 -*-
# -----------------------------------------------------------------------------
# feedmanager - RPC entry point to the feedmanager
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
#
# TODO
#
# - Improve RSS feed for better video and audio feed support
#   https://feedguide.participatoryculture.org/front
# - Torrent downloader (needed for some democracy feeds)
# - Add parallel download function
# - make sure update() is called only once at a time
# - add username / password stuff to rpc or config
#
# External plugins
# - Flickr image feed
# - Gallery support
# - Youtube / Stage6 plugin
#
# ##################################################################

# kaa imports
import kaa.rpc

# feedmanager imports
import manager
import core
import rss

@kaa.rpc.expose('feeds.update')
def update(id=None):
    """
    Update feed with given id or all if id is None
    """
    if id == None:
        return manager.update()
    for c in manager.list_feeds():
        if id == c.id:
            return c.update()
    return False


@kaa.rpc.expose('feeds.list')
def list_feeds():
    """
    List all feeds. Returns a list of dicts.
    """
    feeds = []
    for c in manager.list_feeds():
        feeds.append(c.get_config())
    return feeds


@kaa.rpc.expose('feeds.add')
def add_feed(url, destdir, download=True, num=0, keep=True):
    """
    Add a new feed.
    """
    return manager.add_feed(url, destdir, download, num, keep).get_config()


@kaa.rpc.expose('feeds.remove')
def remove_feed(id):
    """
    Remove feed with given id.
    """
    for c in manager.list_feeds():
        if id == c.id:
            manager.remove_feed(c)
            return True
    return False


def set_database(database):
    """
    Set the database. Called by server at startup.
    """
    core.Feed._db = database
    manager.init()
