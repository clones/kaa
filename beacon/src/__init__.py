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

__all__ = [ 'connect', 'get', 'query', 'NORMAL', 'LARGE' ]

import os
import logging

from client import Client
import thumbnail
from thumbnail import Thumbnail, NORMAL, LARGE

# get logging object
log = logging.getLogger('beacon')

# connected client object
_client = None

def connect():
    """
    Connect to the beacon. A beacon server must be running.
    """
    global _client

    if _client:
        return _client

    log.info('beacon connect')
    thumbnail.connect()
    _client = Client()
    return _client


def get(filename):
    """
    Get object for the given filename.
    """
    if not _client:
        connect()
    return _client.get(filename)


def query(**args):
    """
    Query the database.
    """
    if not _client:
        connect()
    return _client.query(**args)


def add_mountpoint(type, device, directory):
    """
    Add a mountpoint for rom drives
    """
    if not _client:
        connect()
    return _client.add_mountpoint(type, device, directory)

def get_db_info():
    """
    Gets statistics about the database
    """
    if not _client:
        connect()
    return _client.database.get_db_info()
