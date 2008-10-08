# -*- coding: iso-8859-1 -*-
# -----------------------------------------------------------------------------
# __init__.py - Interface to kaa.epg
# -----------------------------------------------------------------------------
# $Id$
# -----------------------------------------------------------------------------
# kaa.epg - EPG Database
# Copyright (C) 2004-2008 Jason Tackaberry, Dirk Meyer, Rob Shortt
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

__all__ = [ 'Channel', 'Program', 'QExpr', 'get_channels', 'get_channel', 'search', 'update' ]

# python imports
import logging

# kaa imports
import kaa
from kaa.db import QExpr

# kaa.epg imports
from version import VERSION
from channel import Channel
from program import Program
from guide import Guide

# get logging object
log = logging.getLogger('epg')

guide = None
server = []

def load(database):
    """
    Load a database
    """
    global guide
    guide = Guide(database)

def connect(address='epg', secret=''):
    """
    Connect to a remote database
    """
    global guide
    from rpc import Client
    guide = Client(address, secret)

def listen(address='epg', secret=''):
    """
    Listen for remote clients
    """
    from rpc import Server
    server.append(Server(guide, address, secret))

def get_channels(sort=False):
    """
    Return a list of all channels
    """
    return guide.get_channels(sort)

def get_channel(name):
    """
    Return the channel with the given name
    """
    return guide.get_channel(name)

def search(channel=None, time=None, utc=False, cls=Program, **kwargs):
    """
    Search the db.
    """
    return guide.search(channel, time, utc, cls, **kwargs)

def get_keywords(associated=None, prefix=None):
    """
    Retrieves a list of keywords in the database.
    """
    return guide.get_keywords(associated, prefix)

def get_genres(associated=None, prefix=None):
    """
    Retrieves a list of genres in the database.
    """
    return guide.get_genres(associated, prefix)

class _SourcesWrapper(object):
    """
    Wrap kaa.epg.sources import to avoid importing
    stuff that is not needed.
    """
    def __call__(self, backend = None, *args, **kwargs):
        """
        Call guide update
        """
        return guide.update(backend, *args, **kwargs)

    @property
    def config(self):
        """
        import sources and get config
        """
        import sources
        return sources.config

update = _SourcesWrapper()
