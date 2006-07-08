# -*- coding: iso-8859-1 -*-
# -----------------------------------------------------------------------------
# server.py - Server interface for Beacon
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


# Python imports
import os
import sys
import logging

# kaa imports
import kaa.rpc
from kaa.weakref import weakref
from kaa.notifier import OneShotTimer, Timer, Callback

# kaa.beacon imports
import parser
from db import *
from monitor import Monitor

# get logging object
log = logging.getLogger('beacon.server')


class Server(object):
    """
    Server for the virtual filesystem to handle write access to the db and
    scanning / monitoring of queries.
    """
    def __init__(self, dbdir):
        log.info('start beacon')
        try:
            self.ipc = kaa.rpc.Server('beacon')
        except IOError, e:
            kaa.beacon.thumbnail.thumbnail.disconnect()
            log.error('beacon: %s' % e)
            time.sleep(0.1)
            sys.exit(0)

        self.ipc.signals['client_connected'].connect(self.client_connect)
        self.ipc.connect(self)
        
        self._dbdir = dbdir
        self._db = Database(dbdir, None)
        self._next_client = 0
        
        # files
        
        self.register_file_type_attrs("video",
            title = (unicode, ATTR_KEYWORDS | ATTR_IGNORE_CASE),
            width = (int, ATTR_SIMPLE),
            height = (int, ATTR_SIMPLE),
            length = (int, ATTR_SIMPLE))

        self.register_file_type_attrs("audio",
            title = (unicode, ATTR_KEYWORDS | ATTR_IGNORE_CASE),
            artist = (unicode, ATTR_KEYWORDS | ATTR_INDEXED | ATTR_IGNORE_CASE),
            album = (unicode, ATTR_KEYWORDS | ATTR_IGNORE_CASE),
            genre = (unicode, ATTR_INDEXED | ATTR_IGNORE_CASE),
            samplerate = (int, ATTR_SIMPLE),
            length = (int, ATTR_SIMPLE),
            bitrate = (int, ATTR_SIMPLE),
            trackno = (int, ATTR_SIMPLE))

        self.register_file_type_attrs("image",
            width = (int, ATTR_SEARCHABLE),
            height = (int, ATTR_SEARCHABLE),
            comment = (unicode, ATTR_KEYWORDS | ATTR_IGNORE_CASE),
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

        # list of current clients
        self._clients = []
        
        # add root mountpoint
        self.add_mountpoint('hd', None, '/')
        self.set_mountpoint('/', 'kaa.beacon.root')

        # commit and wait for the results (there are no results,
        # this code is only used to force waiting until the db is
        # set up.
        self._db.commit()


    def client_connect(self, client):
        """
        Connect a new client to the server.
        """
        client.signals['closed'].connect(self.client_disconnect, client)
        self._next_client += 1
        self._clients.append((self._next_client, client, []))
        client.rpc('connect')(self._next_client, self._dbdir, self._db.get_mountpoints())


    def client_disconnect(self, client):
        """
        IPC callback when a client is lost.
        """
        for client_info in self._clients[:]:
            if client == client_info[1]:
                log.info('disconnect client')
                for m in client_info[2]:
                    m.stop()
                self._clients.remove(client_info)


    def autoshutdown(self, timeout):
        """
        Start autoshutdown.
        """
        if hasattr(self, '_autoshutdown_timer'):
            return
        self._autoshutdown_timer = timeout
        Timer(self._autoshutdown, timeout).start(1)


    def _autoshutdown(self, timeout):
        """
        Timer callback for autoshutdown.
        """
        if len(self._clients) > 0:
            self._autoshutdown_timer = timeout
            return True
        self._autoshutdown_timer -= 1
        if self._autoshutdown_timer == 0:
            log.info('beacon timeout')
            sys.exit(0)
        return True
    

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
        Monitor a directory in the background. One directories with a monitor
        running will update running query monitors.
        """
        self._db.commit()
        data = self._db.query(filename=os.path.realpath(directory))
        items = []
        for i in data._beacon_tree():
            if i._beacon_id:
                break
            items.append(i)
        while items:
            parser.parse(self._db, items.pop(), store=True)
        self._db.commit()
        data._beacon_media.monitor(data)
        
        
    @kaa.rpc.expose('monitor.add')
    def monitor_add(self, client_id, request_id, query):
        """
        Create a monitor object to monitor a query for a client.
        """
        log.info('add monitor %s', query)
        if query and 'parent' in query:
            type, id = query['parent']
            query['parent'] = self._db.query(type=type, id=id)[0]

        for id, client, monitors in self._clients:
            if id == client_id:
                break
        else:
            raise AttributeError('Unknown client id %s', client_id)
        m = Monitor(client, self._db, self, request_id, query)
        monitors.append(m)
    

    @kaa.rpc.expose('monitor.remove')
    def monitor_remove(self, client_id, request_id):
        """
        Create a monitor object to monitor a query for a client.
        """
        log.info('remove monitor %s', client_id)
        for id, client, monitors in self._clients:
            if id == client_id:
                break
        else:
            raise AttributeError('Unknown client id %s', client_id)
        log.debug('remove monitor')
        for m in monitors:
            if m.id == request_id:
                m.stop()
                monitors.remove(m)
                return None
        log.error('unable to find monitor %s:%s', client_id, request_id)
    

    def add_mountpoint(self, type, device, directory):
        """
        Add a mountpoint to the system.
        """
        self._db.add_mountpoint(type, device, directory)


    def set_mountpoint(self, directory, name):
        """
        Set mountpoint to the given name (e.g. load media)
        """
        self._db.set_mountpoint(directory, name)

        
    @kaa.rpc.expose('item.update')
    def update(self, items):
        """
        Update items from the client.
        """
        for dbid, attributes in items:
            self._db.update_object(dbid, **attributes)
        self._db.commit()

        
    @kaa.rpc.expose('item.request')
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

    
    @kaa.rpc.expose('beacon.shutdown')
    def shutdown(self):
        sys.exit(0)
