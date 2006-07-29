# -*- coding: iso-8859-1 -*-
# -----------------------------------------------------------------------------
# __init__.py - interface to kaa.beacon
# -----------------------------------------------------------------------------
# $Id$
#
# -----------------------------------------------------------------------------
# kaa-beacon - A virtual filesystem with metadata
# Copyright (C) 2006 Dirk Meyer
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

__all__ = [ 'connect', 'get', 'query', 'register_filter', 'Item',
            'THUMBNAIL_NORMAL', 'THUMBNAIL_LARGE' ]

# python imports
import os
import logging

# kaa imports
import kaa.notifier

# kaa.beacon imports
from client import Client, CONNECTED, ConnectError
import thumbnail
from thumbnail import NORMAL as THUMBNAIL_NORMAL
from thumbnail import LARGE as THUMBNAIL_LARGE
from query import register_filter, wrap
from item import Item
from hwmon import medialist as media

# get logging object
log = logging.getLogger('beacon')

# connected client object
_client = None
# signals of the client, only valid after calling connect()
signals = {}

def connect():
    """
    Connect to the beacon. A beacon server must be running. This function will
    raise an exception if the client is not connected and the server is not
    running for a connect.
    """
    global _client
    global signals

    if _client:
        return _client

    log.info('beacon connect')
    _client = Client()
    thumbnail.connect()
    signals = _client.signals
    return _client


def get(filename):
    """
    Get object for the given filename. This function will raise an exception if
    the client is not connected and the server is not running for a connect.
    If the client is still connecting or reconnecting, this function will block
    using kaa.notifier.step.
    """
    if not _client:
        connect()
    return _client.get(filename)


def query(**args):
    """
    Query the database. This function will raise an exception if the
    client is not connected and the server is not running for a connect.
    """
    if not _client:
        connect()
    return _client.query(**args)


def monitor(directory):
    """
    Monitor a directory with subdirectories for changes. This is done in
    the server and will keep the database up to date.
    """
    if not _client:
        connect()
    return _client.monitor_directory(directory)


def get_db_info():
    """
    Gets statistics about the database. This function will block using
    kaa.notifier.step() until the client is connected.
    """
    if not _client:
        connect()
    while not _client.status == CONNECTED:
        kaa.notifier.step()
    return _client.db.get_db_info()
