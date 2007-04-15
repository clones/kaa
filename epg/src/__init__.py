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
import kaa.notifier
from kaa.db import QExpr

# kaa.epg imports
from version import VERSION
from config import config
from channel import Channel
from program import Program
from client import Client, DISCONNECTED, CONNECTING, CONNECTED
from server import Server
from sources import *

# get logging object
log = logging.getLogger('epg')

# connected client object
guide = Client()

def connect(address = 'epg', auth_secret = ''):
    """
    Connect to the epg server with the given address and auth secret.
    """
    if guide.status != DISCONNECTED:
        log.warning('connecting to a new epg database')
    guide.connect(address, auth_secret)
    return guide


def get_channels(sort=False):
    """
    Return a list of all channels.
    """
    if guide.status == DISCONNECTED:
        connect()
    return guide.get_channels(sort)


def get_channel(name):
    """
    Return the channel with the given name.
    """
    if guide.status == DISCONNECTED:
        connect()
    return guide.get_channel(name)


def search(channel=None, time=None, block=False, **kwargs):
    """
    Search the db. This will call the search function on server side using
    kaa.ipc. This function will return an InProgress object. If block is
    True the function to block using kaa.notifier.step() until the result
    arrived from the server.
    """
    if guide.status == DISCONNECTED:
        connect()
        while block and guide.status == CONNECTING:
            kaa.notifier.step()

    if block:
        wait = guide.search(channel, time, **kwargs)
        while not wait.is_finished:
            kaa.notifier.step()
        return wait()
    return guide.search(channel, time, **kwargs)


def is_connected():
    return guide and guide.status == CONNECTED
