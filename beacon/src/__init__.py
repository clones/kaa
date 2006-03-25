# -*- coding: iso-8859-1 -*-
# -----------------------------------------------------------------------------
# __init__.py - interface to kaa.beacon
# -----------------------------------------------------------------------------
# $Id$
#
# -----------------------------------------------------------------------------
# kaa-beacon - A virtual filesystem with metadata
# Copyright (C) 2005 Dirk Meyer
#
# First Edition: Dirk Meyer <dmeyer@tzi.de>
# Maintainer:    Dirk Meyer <dmeyer@tzi.de>
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

from kaa import ipc
from client import Client
import thumbnail
from thumbnail import Thumbnail, NORMAL, LARGE

# get logging object
log = logging.getLogger('beacon')

# connected client object
_client = None

def connect(database=None):
    """
    Connect to the beacon database dir given by 'database'. Id 'database' is None, the
    client will only connect to the thumbnailer. A beacon server must be running.
    """
    global _client

    if _client:
        return _client

    log.info('connect to thumbnailer')
    thumbnail.connect()

    if not database:
        return None
    
    log.info('connect to %s' % database)
    _client = Client(database)
    return _client


def get(filename):
    """
    Get object for the given filename.
    """
    if not _client:
        raise RuntimeError('beacon not connected')
    return _client.get(filename)


def query(**args):
    """
    Query the database.
    """
    if not _client:
        raise RuntimeError('beacon not connected')
    return _client.query(**args)
