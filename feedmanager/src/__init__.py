# -*- coding: iso-8859-1 -*-
# -----------------------------------------------------------------------------
# feedmanager - RPC entry point to the feedmanager
# -----------------------------------------------------------------------------
# $Id$
#
# -----------------------------------------------------------------------------
# kaa.feedmanager - Manage RSS/Atom Feeds
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

# python imports
import os

# kaa imports
import kaa.rpc

# feedmanager imports
import manager
import core
import rss

class Feed(dict):
    def remove(self):
        """
        Remove feed
        """
        for c in manager.list_feeds():
            if self.get('id') == c.id:
                manager.remove_feed(c)
                return True
        return False

    def update(self):
        """
        Update feed
        """
        for c in manager.list_feeds():
            if self.get('id') == c.id:
                return c.update()
        return False

def list_feeds():
    """
    List all feeds. Returns a list of dicts.
    """
    feeds = []
    for c in manager.list_feeds():
        feeds.append(Feed(c.get_config()))
    return feeds


def add_feed(url, destdir, download=True, num=0, keep=True):
    """
    Add a new feed.
    """
    return Feed(manager.add_feed(url, destdir, download, num, keep).get_config())


def set_database(database):
    """
    Set the database. Called by server at startup.
    """
    core.Feed.IMAGEDIR = os.path.join(database, 'images')
    if not os.path.isdir(core.Feed.IMAGEDIR):
        os.makedirs(core.Feed.IMAGEDIR)
    manager.init(os.path.join(database, 'feeds.xml'))
