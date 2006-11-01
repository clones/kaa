# -*- coding: iso-8859-1 -*-
# -----------------------------------------------------------------------------
# __init__.py - Interface to kaa.epg
# -----------------------------------------------------------------------------
# $Id$
# -----------------------------------------------------------------------------
# kaa.epg - EPG Database
# Copyright (C) 2004-2006 Jason Tackaberry, Dirk Meyer, Rob Shortt
#
# First Edition: Jason Tackaberry <tack@sault.org>
#
# Please see the file AUTHORS for a complete list of authors.
#
# This library is free software; you can redistribute it and/or modify
# it under the terms of the GNU Lesser General Public License version
# 2.1 as published by the Free Software Foundation.
#
# This library is distributed in the hope that it will be useful, but
# WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
# Lesser General Public License for more details.
#
# You should have received a copy of the GNU Lesser General Public
# License along with this library; if not, write to the Free Software
# Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA
# 02110-1301 USA
#
# -----------------------------------------------------------------------------

__all__ = [ 'connect', 'Channel', 'Program', 'Client', 'Server', 'QExpr',
            'get_channels', 'get_channel', 'search', 'sources' ]

# python imports
import logging

# kaa imports
from kaa.db import QExpr

# kaa.epg imports
from channel import Channel
from program import Program
from client import Client, DISCONNECTED, CONNECTING, CONNECTED
from server import Server
from source import sources

# kaa.epg import for internal use
from util import cmp_channel

# get logging object
log = logging.getLogger('epg')

# connected client object
guide = None

def connect(address, auth_secret=''):
    """
    Connect to the epg server with the given address.
    """
    global guide

    if guide and not guide.status == DISCONNECTED:
        log.warning('connecting to a new epg database')

    guide = Client(address, auth_secret)
    return guide


def get_channels(sort=False):
    """
    Return a list of all channels.
    """
    if guide and not guide.status == DISCONNECTED:
        if sort:
            channels = guide.get_channels()[:]
            channels.sort(lambda a, b: cmp(a.name, b.name))
            channels.sort(lambda a, b: cmp_channel(a, b))
            return channels
        return guide.get_channels()
    return []


def get_channel(name):
    """
    Return the channel with the given name.
    """
    if guide and not guide.status == DISCONNECTED:
        return guide.get_channel(name)
    return []


def search(*args, **kwargs):
    """
    Search the epg.
    """
    if guide and not guide.status == DISCONNECTED:
        try:
            return guide.search(*args, **kwargs)
        except Exception, e:
            log.exception('kaa.epg.search failed')
    return []

def is_connected():
    return guide and guide.status == CONNECTED
