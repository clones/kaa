# -*- coding: iso-8859-1 -*-
# -----------------------------------------------------------------------------
# client.py - client part of the epg
# -----------------------------------------------------------------------------
# $Id: guide.py 3543 2008-09-12 20:05:37Z dmeyer $
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

__all__ = [ 'Client', 'Server' ]

# python imports
import logging

# kaa imports
import kaa
import kaa.rpc

# kaa.epg imports
from channel import Channel
from guide import Guide
from util import EPGError

# get logging object
log = logging.getLogger('epg')

class Client(Guide):
    """
    EPG client class to access the epg on server side.
    """

    DISCONNECTED = 'DISCONNECTED'
    CONNECTING = 'CONNECTING'
    CONNECTED = 'CONNECTED'

    def __init__(self, address, secret):
        self._status = Client.DISCONNECTED
        self._channels_by_name = {}
        self._channels_by_db_id = {}
        self._channels_by_tuner_id = {}
        self._channels = []
        self.rpc = None
        self.signals = kaa.Signals('connected', 'disconnected')
        self._server_address = address
        self._server_secret = secret
        self.connect()

    def connect(self):
        """
        Connect to EPG server.
        """
        try:
            server = kaa.rpc.Client(self._server_address, auth_secret=self._server_secret)
            server.connect(self)
        except kaa.rpc.ConnectError:
            return kaa.OneShotTimer(self.connect).start(1)
        server.signals['closed'].connect_weak(self._disconnected)
        self._status = Client.CONNECTING
        self.rpc = server.rpc

    def _disconnected(self):
        """
        Signal callback when server disconnects.
        """
        log.debug('kaa.epg client disconnected')
        self._status = Client.DISCONNECTED
        self.signals["disconnected"].emit()
        self.rpc = None
        self.connect()

    @kaa.rpc.expose('sync')
    def _sync(self, channels, max_program_length, num_programs):
        """
        (re)load some static information
        """
        self._channels_by_name = {}
        self._channels_by_db_id = {}
        self._channels_by_tuner_id = {}
        self._channels = []
        for objrow in channels:
            chan = Channel(objrow)
            self._channels_by_name[chan.name] = chan
            self._channels_by_db_id[chan.db_id] = chan
            for t in chan.tuner_id:
                if self._channels_by_tuner_id.has_key(t):
                    log.warning('loading channel %s with tuner_id %s already claimed by channel %s',
                                chan.name, t, self._channels_by_tuner_id[t].name)
                else:
                    self._channels_by_tuner_id[t] = chan
            self._channels.append(chan)
        # get attributes from server and store local
        self._max_program_length = max_program_length
        self._num_programs = num_programs
        if self._status == Client.CONNECTING:
            self._status = Client.CONNECTED
            self.signals["connected"].emit()

    def search(self, channel=None, time=None, **kwargs):
        """
        Search the db

        The time kwarg is a unix timestamp or 2-tuple of timestamps.  In the
        former case, all programs playing at the given time are returned.  In
        the latter case, the 2-tuple represents a start and end range, and all
        programs playing within the range are returned.  If stop is 0, then it
        is treated as infinity.
        """
        if self._status != Client.CONNECTED:
            raise EPGError('Client is not connected')
        return self.rpc('search', channel, time, **kwargs)

    def update(self):
        """
        Update the database
        """
        if self._status != Client.CONNECTED:
            raise EPGError('Client is not connected')
        return self.rpc('update')


class Server(object):
    """
    Server class for the epg.
    """
    def __init__(self, guide, address, secret):
        self._clients = []
        # initial sync
        self.guide = guide
        self._rpc = kaa.rpc.Server(address, secret)
        self._rpc.signals['client_connected'].connect(self.client_connected)
        self._rpc.connect(self)

    @kaa.rpc.expose('search')
    def query(self, channel, time, **kwargs):
        """
        Remote search
        """
        return self.guide.search(channel, time, **kwargs)

    @kaa.rpc.expose('update')
    def update(self, channel, time, **kwargs):
        """
        Remote search
        """
        return self.guide.update()

    def client_connected(self, client):
        """
        Connect a new client to the server.
        """
        client.rpc('sync', self.guide._db.query(type = "channel"),
            self.guide._max_program_length, self.guide._num_programs)
        client.signals['closed'].connect(self.client_closed, client)
        self._clients.append(client)

    def client_closed(self, client):
        """
        Callback when a client disconnects.
        """
        log.info('Client disconnected: %s', client)
        self._clients.remove(client)
