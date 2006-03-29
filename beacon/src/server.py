# -*- coding: iso-8859-1 -*-
# -----------------------------------------------------------------------------
# server.py - Server interface for Beacon
# -----------------------------------------------------------------------------
# $Id$
#
# TODO: handle all the FIXME and TODO comments inside this file and
#       add docs for functions, variables and how to use this file
#
# -----------------------------------------------------------------------------
# kaa-beacon - A virtual filesystem with metadata
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
import sys
import logging

# kaa imports
from kaa import ipc
from kaa.weakref import weakref
from kaa.notifier import OneShotTimer, Timer

# kaa.beacon imports
import parser
from db import *
from monitor import Monitor

# get logging object
log = logging.getLogger('beacon')

# ipc debugging
# ipc.DEBUG = 1

class Server(object):
    """
    Server for the virtual filesystem to handle write access to the db and
    scanning / monitoring of queries.
    """
    def __init__(self, dbdir):
        self._db = Database(dbdir, None)
        self._next_client = 0
        
        # files
        
        self.register_file_type_attrs("video",
            title = (unicode, ATTR_KEYWORDS),
            width = (int, ATTR_SIMPLE),
            height = (int, ATTR_SIMPLE),
            length = (int, ATTR_SIMPLE))

        self.register_file_type_attrs("audio",
            title = (unicode, ATTR_KEYWORDS),
            artist = (unicode, ATTR_KEYWORDS | ATTR_INDEXED),
            album = (unicode, ATTR_KEYWORDS),
            genre = (unicode, ATTR_INDEXED),
            samplerate = (int, ATTR_SIMPLE),
            length = (int, ATTR_SIMPLE),
            bitrate = (int, ATTR_SIMPLE),
            trackno = (int, ATTR_SIMPLE))

        self.register_file_type_attrs("image",
            width = (int, ATTR_SEARCHABLE),
            height = (int, ATTR_SEARCHABLE),
            date = (unicode, ATTR_SEARCHABLE))

        # tracks for rom discs or iso files
        
        self.register_track_type_attrs("dvd",
            audio = (list, ATTR_SIMPLE),
            chapters = (int, ATTR_SIMPLE),
            subtitles = (list, ATTR_SIMPLE))

        self.register_track_type_attrs("vcd",
            audio = (list, ATTR_SIMPLE))

        self.register_track_type_attrs("cd",
            title = (unicode, ATTR_KEYWORDS),
            artist = (unicode, ATTR_KEYWORDS | ATTR_INDEXED),
            album = (unicode, ATTR_KEYWORDS),
            genre = (unicode, ATTR_INDEXED))

        # TODO: add more known types and support data tracks on
        # audio cds

        # list of current clients
        self._clients = []
        
        # add root mountpoint
        self.add_mountpoint(None, '/')
        self.set_mountpoint('/', 'kaa.beacon.root')

        # commit and wait for the results (there are no results,
        # this code is only used to force waiting until the db is
        # set up.
        self._db.commit()


    def register_file_type_attrs(self, name, **kwargs):
        """
        Register new attrs and types for files. The basics are already
        in the db by the __init__ function of this class.
        """
        return self._db.register_object_type_attrs(name, **kwargs)


    def register_track_type_attrs(self, name, **kwargs):
        """
        Register new attrs and types for files. The basics are already
        in the db by the __init__ function of this class.
        """
        return self._db.register_object_type_attrs('track_%s' % name, **kwargs)


    def monitor_dir(self, directory):
        """
        """
        self._db.commit()
        data = self._db.query(filename=directory)
        items = []
        for i in data._beacon_tree():
            if i._beacon_id:
                break
            items.append(i)
        while items:
            parser.parse(self._db, items.pop(), store=True)
        self._db.commit()
        data._beacon_media.monitor(data)
        
        
    def monitor(self, client_id, request_id, query):
        """
        Create a monitor object to monitor a query for a client.
        """
        if query and 'parent' in query:
            type, id = query['parent']
            query['parent'] = self._db.query(type=type, id=id)[0]

        for id, client, callback, monitors in self._clients:
            if id == client_id:
                break
        else:
            raise AttributeError('Unknown client id %s', client_id)
        if not query:
            log.debug('remove monitor')
            for m in monitors:
                if m.id == request_id:
                    m.stop()
                    monitors.remove(m)
                    return None
            log.error('unable to find monitor %s:%s', client_id, request_id)
            return None
            
        m = Monitor(callback, self._db, self, request_id, query)
        monitors.append(m)
        return None
    

    def add_mountpoint(self, device, directory):
        """
        Add a mountpoint to the system.
        """
        if self._db.add_mountpoint(device, directory):
            for id, client, notification, monitors in self._clients:
                client.database.add_mountpoint(device, directory, __ipc_oneway=True)


    def set_mountpoint(self, directory, name):
        """
        Set mountpoint to the given name (e.g. load media)
        """
        if self._db.set_mountpoint(directory, name):
            for id, client, notification, monitors in self._clients:
                client.database.set_mountpoint(directory, name)
            return True
        return False

        
    def connect(self, client, callback):
        """
        Connect a new client to the server.
        """
        self._next_client += 1
        self._clients.append((self._next_client, client, callback, []))
        for device, directory, name in self._db.get_mountpoints():
            client.database.add_mountpoint(device, directory)
            client.database.set_mountpoint(directory, name)
        return self._next_client


    def update(self, items):
        """
        Update items from the client.
        """
        for dbid, attributes in items:
            self._db.update_object(dbid, **attributes)
        # TODO: they are changed now, send update to every other client
        self._db.commit()

        
    def request(self, filename):
        self._db.commit()
        data = self._db.query(filename=filename)
        items = []
        for i in data._beacon_tree():
            if i._beacon_id:
                break
            items.append(i)
        while items:
            parser.parse(self._db, items.pop(), store=True)
        self._db.commit()
        return data._beacon_data

    
    def __del__(self):
        """
        Debug in __del__.
        """
        return 'del', self
            
        
# internal list of server
_server = {}
_num_client = 0

def connect(dbdir):
    """
    Connect to a server object. Each server object handles one db dir.
    Different clients can use the same server object.
    """
    log.info('connect to %s' % dbdir)

    global _num_client
    _num_client += 1
    
    # TODO: delete databases not used anymore
    
    if not dbdir in _server:
        log.info('create server object')
        server = Server(dbdir)
        # TODO: use weakref
        _server[dbdir] = server
    return _server[dbdir]


def _client_closed(client):
    global _num_client
    for server in _server.values():
        for client_info in server._clients:
            if ipc.get_ipc_from_proxy(client_info[1]) == client:
                log.warning('disconnect client')
                for m in client_info[3]:
                    m.stop()
                server._clients.remove(client_info)
                _num_client -= 1


def autoshutdown_step(timeout):
    global shutdown_timer
    if _num_client > 0:
        shutdown_timer = timeout
        return True
    shutdown_timer -= 1
    if shutdown_timer == 0:
        log.info('beacon timeout')
        sys.exit(0)
    return True
    

def autoshutdown(timeout):
    global shutdown_timer
    shutdown_timer = timeout
    Timer(autoshutdown_step, timeout).start(1)
    
