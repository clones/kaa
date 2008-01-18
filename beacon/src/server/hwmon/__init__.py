# -*- coding: iso-8859-1 -*-
# -----------------------------------------------------------------------------
# hwmon__init__.py - hardware monitor
# -----------------------------------------------------------------------------
# $Id$
#
# -----------------------------------------------------------------------------
# kaa.beacon.server - A virtual filesystem with metadata
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

# python imports
import time
import socket

# kaa.beacon.server.hwmon imports
from client import Client as _Client

_client = None

def connect():
    """
    Connect to hardware monitor process. This function will block
    if connection is not possible (timeout 3 sec).
    """
    global _client
    if _client:
        return _client
    start = time.time()
    while True:
        try:
            _client = _Client()
            return _client
        except socket.error, e:
            if start + 3 < time.time():
                # start time is up, something is wrong here
                raise RuntimeError('unable to connect to hardware monitor')
            time.sleep(0.01)


def set_database(handler, db, rootfs=None):
    _client.set_database(handler, db, rootfs)


def get_client():
    return _client
