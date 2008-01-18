# -*- coding: iso-8859-1 -*-
# -----------------------------------------------------------------------------
# beacon/feedmanager.py - Beacon server plugin
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
import logging
from logging.handlers import RotatingFileHandler

# kaa imports
import kaa
import kaa.notifier.url
import kaa.feedmanager
import kaa.rpc

# plugin config object
config = kaa.feedmanager.config


class IPC(object):
    """
    Class to connect the feedmanager to the beacon server ipc.
    """

    @kaa.rpc.expose('feeds.list')
    def list(self):
        """
        List feeds.
        """
        return kaa.feedmanager.list_feeds()

    @kaa.rpc.expose('feeds.add')
    def add(self, url, destdir, download=True, num=0, keep=True):
        """
        Add a feed.
        """
        return kaa.feedmanager.add_feed(url, destdir, download, num, keep)

    @kaa.rpc.expose('feeds.remove')
    def remove(self, feed):
        """
        Remove the given feed.
        """
        if isinstance(feed, dict):
            feed = feed.get('id')
        return kaa.feedmanager.remove_feed(feed)

    @kaa.rpc.expose('feeds.update')
    def update(self, feed):
        """
        Update the given feed.
        """
        if isinstance(feed, dict):
            feed = feed.get('id')
        return kaa.feedmanager.update_feed(feed)


def plugin_init(server, db):
    """
    Init the plugin.
    """
    # configure logger
    log = logging.getLogger('feedmanager')
    log.setLevel(logging.DEBUG)

    logfile = os.path.join(db.get_directory(), 'feedmanager/log')
    if os.path.dirname(logfile) and not os.path.isdir(os.path.dirname(logfile)):
        os.makedirs(os.path.dirname(logfile))
    # create rotating log file with 1MB for each file with a backup of 3
    handler = RotatingFileHandler(logfile, maxBytes=1000000, backupCount=3)
    f = logging.Formatter('%(asctime)s %(levelname)-8s [%(name)6s] '+\
                          '%(filename)s %(lineno)s: %(message)s')
    handler.setFormatter(f)
    log.addHandler(handler)

    # use ~/.beacon/feedmanager as base dir
    database = os.path.join(db.get_directory(), 'feedmanager')
    kaa.feedmanager.set_database(database)
    server.ipc.connect(IPC())
    # add password information
    for auth in kaa.feedmanager.config.authentication:
        kaa.notifier.url.add_password(None, auth.site, auth.username, auth.password)
