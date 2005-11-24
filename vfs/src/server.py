# -*- coding: iso-8859-1 -*-
# -----------------------------------------------------------------------------
# server.py - Server interface for the VFS
# -----------------------------------------------------------------------------
# $Id$
#
# TODO: handle all the FIXME and TODO comments inside this file and
#       add docs for functions, variables and how to use this file
#
# -----------------------------------------------------------------------------
# kaa-vfs - A virtual filesystem with metadata
# Copyright (C) 2005 Dirk Meyer
#
# First Edition: Dirk Meyer <dmeyer@tzi.de>
# Maintainer:    Dirk Meyer <dmeyer@tzi.de>
#
# Please see the file doc/CREDITS for a complete list of authors.
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


# Python imports
import os
import logging

# kaa imports
from kaa.base import ipc, weakref
from kaa.notifier import OneShotTimer

# kaa.vfs imports
from db import *
from monitor import Monitor

# get logging object
log = logging.getLogger('vfs')

# ipc debugging
# ipc.DEBUG = 1

class Server(object):
    """
    Server for the virtual filesystem to handle write access to the db and
    scanning / monitoring of queries.
    """
    def __init__(self, dbdir):
        self._db = Database(dbdir, False)

        self.register_object_type_attrs("video",
            title = (unicode, ATTR_KEYWORDS),
            width = (int, ATTR_SIMPLE),
            height = (int, ATTR_SIMPLE),
            length = (int, ATTR_SIMPLE))

        self.register_object_type_attrs("audio",
            title = (unicode, ATTR_KEYWORDS),
            artist = (unicode, ATTR_KEYWORDS | ATTR_INDEXED),
            album = (unicode, ATTR_KEYWORDS),
            genre = (unicode, ATTR_INDEXED),
            samplerate = (int, ATTR_SIMPLE),
            length = (int, ATTR_SIMPLE),
            bitrate = (int, ATTR_SIMPLE),
            trackno = (int, ATTR_SIMPLE))

        self.register_object_type_attrs("image",
            width = (int, ATTR_SEARCHABLE),
            height = (int, ATTR_SEARCHABLE),
            date = (unicode, ATTR_SEARCHABLE))

        # TODO: add more known types

        # list of current clients
        self._clients = []

        # add root mountpoint
        self.add_mountpoint(None, '/')
        self.set_mountpoint('/', 'kaa.vfs.root')
        
        # commit and wait for the results (there are no results,
        # this code is only used to force waiting until the db is
        # set up.
        self._db.commit()
        

    def register_object_type_attrs(self, *args, **kwargs):
        """
        Register new attrs and types for objects. The basics are already
        in the db by the __init__ function of this class.
        """
        return self._db.register_object_type_attrs(*args, **kwargs)


    def monitor(self, callback, id, **query):
        """
        Create a monitor object to monitor a query for a client.
        """
        monitor = Monitor(callback, self._db, self, id, query)
        log.debug('create %s' % monitor)
        callback(id, 'connect', monitor)
        monitor.update()
        return None
    

    def add_mountpoint(self, device, directory):
        """
        Add a mountpoint to the system.
        """
        if self._db.add_mountpoint(device, directory):
            for client in self._clients:
                client.database.add_mountpoint(device, directory, __ipc_oneway=True)


    def set_mountpoint(self, directory, name):
        """
        Set mountpoint to the given name (e.g. load media)
        """
        if self._db.set_mountpoint(directory, name):
            for client in self._clients:
                client.database.set_mountpoint(directory, name)
            return True
        return False

        
    def connect(self, client):
        """
        Connect a new client to the server.
        """
        self._clients.append(client)
        for device, directory, name in self._db.get_mountpoints():
            client.database.add_mountpoint(device, directory)
            client.database.set_mountpoint(directory, name)


    def __del__(self):
        """
        Debug in __del__.
        """
        return 'del', self
            
        
# internal list of server
_server = {}

def connect(dbdir):
    """
    Connect to a server object. Each server object handles one db dir.
    Different clients can use the same server object.
    """
    log.info('connect to %s' % dbdir)

    # TODO: delete databases not used anymore

    if not dbdir in _server:
        log.info('create server object')
        server = Server(dbdir)
        # TODO: use weakref
        _server[dbdir] = server
    return _server[dbdir]


def _client_closed(client):
    print client
    
# connect to the ipc code
_ipc = ipc.IPCServer('vfs')
_ipc.register_object(connect, 'vfs')
