# -*- coding: iso-8859-1 -*-
# -----------------------------------------------------------------------------
# rpc.py - Client/Server for kaa.epg over kaa.rpc
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

__all__ = [ 'Client', 'Server' ]

# python imports
import logging

# kaa imports
import kaa
import kaa.rpc
from kaa.utils import localtime2utc

# kaa.epg imports
from channel import Channel
from program import Program
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
        kaa.OneShotTimer(self.connect).start(1)

    @kaa.rpc.expose()
    def _sync(self, channels):
        """
        Connect from server
        """
        self._channels_by_name = {}
        self._channels_by_db_id = {}
        self._channels_by_tuner_id = {}
        for chan in channels:
            self._channels_by_name[chan.name] = chan
            self._channels_by_db_id[chan.db_id] = chan
            for t in chan.tuner_id:
                self._channels_by_tuner_id[t] = chan
        if self._status == Client.CONNECTING:
            self._status = Client.CONNECTED
            self.signals["connected"].emit()

    @kaa.coroutine()
    def search(self, channel=None, time=None, utc=False, cls=None, **kwargs):
        """
        Search the db

        @param channel: kaa.epg.Channel or list of Channels or None for all
        @param time: int/float or list of start,stop or None for all, stop=0
            means until the end of the guide data.
        @param cls: class to use to create programs or None to return raw data
        """
        # FIXME: this function has a different default value. It uses cls=None
        # while all the other classes use cls=Program. The effect is the same
        # because search in __init__ sets cls=Program. The reason is that the
        # wrap function in kaa.utils using for kaa.coroutine does not work with
        # classes as default argument.
        if self._status == Client.DISCONNECTED:
            raise EPGError('Client is not connected')
        if not utc:
            # convert to utc because the server may have a different
            # local timezone set.
            if isinstance(time, (int, float, long)):
                time = localtime2utc(time)
            else:
                time = [ localtime2utc(t) for t in time ]
        query_data = yield self.rpc('search', channel, time, True, None, **kwargs)
        # Convert raw search result data from the server into python objects.
        results = []
        channel = None
        for row in query_data:
            if not channel or row['parent_id'] != channel.db_id:
                if row['parent_id'] not in self._channels_by_db_id:
                    continue
                channel = self._channels_by_db_id[row['parent_id']]
            results.append(cls(channel, row, utc))
        yield results

    def update(self):
        """
        Update the database
        """
        if self._status == Client.DISCONNECTED:
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

    @kaa.rpc.expose()
    def search(self, channel, time, utc, cls, **kwargs):
        """
        Remote search
        """
        return self.guide.search(channel, time, utc, cls, **kwargs)

    @kaa.rpc.expose()
    def update(self):
        """
        Remote update
        """
        return self.guide.update()

    def client_connected(self, client):
        """
        Connect a new client to the server.
        """
        client.rpc('_sync', self.guide._channels_by_name.values())
        client.signals['closed'].connect(self.client_closed, client)
        self._clients.append(client)

    def client_closed(self, client):
        """
        Callback when a client disconnects.
        """
        log.info('Client disconnected: %s', client)
        self._clients.remove(client)
