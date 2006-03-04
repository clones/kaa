# -*- coding: iso-8859-1 -*-
# -----------------------------------------------------------------------------
# __init__.py - interface to kaa.vfs
# -----------------------------------------------------------------------------
# $Id$
#
# -----------------------------------------------------------------------------
# kaa-vfs - A virtual filesystem with metadata
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

__all__ = [ 'connect', 'get', 'query' ]

import os
import logging

from kaa.base import ipc
from client import Client

# connected client object
_client = None

def connect(vfsdb, logfile=None, loglevel=logging.INFO):
    """
    Connect to the vfs database dir given by 'vfsdb'. A server will be started
    if no server is running. The new server will print debug output to the
    given logfile. If a server is already running, logfile has no effect. If
    a loglevel is given and the server will be started, it will use the given
    loglevel. If no logfile is given, the server will log to vfsdb/log.
    The server can be used by different clients in different applications if
    the are started by the same user. It will shutdown if no client is connected
    for over 5 seconds.
    """
    global _client

    if _client:
        return _client
    
    # check logfile
    if not logfile:
        logfile = os.path.join(vfsdb, 'log')
    # get server filename
    server = os.path.join(os.path.dirname(__file__), 'server.py')

    _client = ipc.launch([server, logfile, str(loglevel)], 5, Client, vfsdb)
    return _client


def get(filename):
    """
    Get object for the given filename.
    """
    if not _client:
        raise RuntimeError('vfs not connected')
    return _client.get(filename)


def query(**args):
    """
    Query the database.
    """
    if not _client:
        raise RuntimeError('vfs not connected')
    return _client.query(**args)
