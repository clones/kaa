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
from datetime import datetime

# kaa imports
import kaa
import kaa.rpc
import kaa.dateutils

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

    def __init__(self, address, secret):
        self.connected = False
        self._channels_by_name = {}
        self._channels_by_db_id = {}
        self._channels_by_tuner_id = {}
        self.rpc = None
        self.signals = kaa.Signals('connected', 'disconnected')
        self._server_address = address
        self._server_secret = secret
        self.channel = kaa.rpc.connect(self._server_address, auth_secret=self._server_secret, retry=1)
        self.channel.register(self)
        self.channel.signals['closed'].connect_weak(self._disconnected)

    def _disconnected(self):
        """
        Signal callback when server disconnects.
        """
        log.info('kaa.epg client disconnected')
        self.connected = False
        self.signals["disconnected"].emit()

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
        if not self.connected:
            log.info('kaa.epg client connected')
            self.connected = True
            self.signals["connected"].emit()

    @kaa.coroutine()
    def search(self, channel=None, time=None, cls=Program, **kwargs):
        """
        Search the EPG for programs.

        :param channel: Indicates the channel or channels within which to search
                        for programs.  Channels are specified by :class:`~kaa.epg.Channel`
                        objects.  If None is specified, all channels are searched.
        :type channel: :class:`~kaa.epg.Channel` object, list, or None
        :param time: Specifies a point in time or range of times.  If a range is
                     specified, a 2-tuple is used representing (start, stop).
                     Times can be specified as UNIX timestamps (seconds since
                     epoch UTC), or as Python datetime objects.  If a naive
                     datetime object is given (i.e. no tzinfo assigned), it is
                     treated as localtime.  A stop time of 0 means infinity. If
                     any part of the program's runtime intersects with the time
                     or time range provided, it matches.
        :type time: int or float, datetime, or 2-tuple of previous
        :param cls: Class used for program results.  The default is to return
                    :class:`~kaa.epg.Program` objects.  If None is given,
                    the raw query data (from kaa.db) is returned.
        :return: a list of :class:`~kaa.epg.Program` objects (or raw database
                 rows if ``cls=None``) matching the search criteria.


        Keyword arguments corresponding to the searchable columns of the
        underlying kaa.db database can also be specified.  They are:

            * ``title``: the title of the program (unicode)
            * ``desc``: the program's full description (unicode)
            * ``start``: program start time as unix timestamp (seconds since
                         epoch in UTC); you probably want to use the time kwarg
                         instead.
            * ``stop``: program start time as unix timestamp; you probably want
                        to use the time kwarg instead.
            * ``genres``: one or more genres (unicode or list of unicode); all
                          possible genres currently in the EPG can be gotten
                          using :meth:`~Guide.get_genres`.
            * ``date``: Original air date of the program, expressed as a UNIX
                        timestamp (int).
            * ``year``: for movies, the year of release (int).
            * ``score``: the critical rating for the program, especially for
                         movies (float); out of 4.0.
            * ``keywords``: one or more keywords which match against the program
                            title, description, and subtitle.

        With the exception of ``keywords`` and ``genres``, a :class:`~kaa.db.QExpr`
        object can be used with any of the above kwargs.
        """
        def convert(dt):
            'Converts a time to a unix timestamp (seconds since epoch UTC)'
            import time as _time
            if isinstance(dt, (int, float, long)):
                return dt
            if not dt.tzinfo:
                # No tzinfo, treat as localtime.
                return _time.mktime(dt.timetuple())
            # tzinfo present, convert to local tz (which is what time.mktime wants)
            return _time.mktime(dt.astimezone(kaa.dateutils.local).timetuple())

        if self.channel.status == kaa.rpc.DISCONNECTED:
            raise EPGError('Client is not connected')
        # convert to UTC because the server may have a different
        # local timezone set.
        if time is not None:
            if isinstance(time, (tuple, list)):
                time = convert(time[0]), convert(time[1])
            else:
                time = convert(time)
        query_data = yield self.channel.rpc('search', channel, time, True, None, **kwargs)
        # Convert raw search result data from the server into python objects.
        results = []
        channel = None
        for row in query_data:
            if not channel or row['parent_id'] != channel.db_id:
                if row['parent_id'] not in self._channels_by_db_id:
                    continue
                channel = self._channels_by_db_id[row['parent_id']]
            results.append(cls(channel, row))
        yield results

    def update(self):
        """
        Update the database
        """
        if self.channel.status == kaa.rpc.DISCONNECTED:
            raise EPGError('Client is not connected')
        return self.channel.rpc('update')


class Server(object):
    """
    Server class for the epg.
    """
    def __init__(self, guide, address, secret):
        self._clients = []
        # initial sync
        self.guide = guide
        self._rpc = kaa.rpc.Server(address, secret)
        self._rpc.signals['client-connected'].connect(self.client_connected)
        self._rpc.register(self)

    @kaa.rpc.expose()
    def search(self, channel, time, cls, **kwargs):
        """
        Remote search
        """
        return self.guide.search(channel, time, cls, **kwargs)

    @kaa.rpc.expose()
    def get_keywords(self, associated=None, prefix=None):
        return self.guide.get_keywords(associated, prefix)

    @kaa.rpc.expose()
    def get_genres(self, associated=None, prefix=None):
        return self.guide.get_genres(associated, prefix)

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
