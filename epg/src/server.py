# -*- coding: iso-8859-1 -*-
# -----------------------------------------------------------------------------
# server.py - server part of the epg
# -----------------------------------------------------------------------------
# $Id$
# -----------------------------------------------------------------------------
# kaa.epg - EPG Database
# Copyright (C) 2004-2006 Jason Tackaberry, Dirk Meyer, Rob Shortt
#
# First Edition: Jason Tackaberry <tack@sault.org>
# Maintainer:    Dirk Meyer <dischi@freevo.org>
#                Rob Shortt <rob@tvcentric.com>
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
## You should have received a copy of the GNU General Public License along
# with this program; if not, write to the Free Software Foundation, Inc.,
# 59 Temple Place, Suite 330, Boston, MA 02111-1307 USA
#
# -----------------------------------------------------------------------------

__all__ = [ 'Server']

# python imports
import logging
from types import ListType

# kaa imports
from kaa.db import *
import kaa.rpc

from kaa.notifier import Signal

# kaa.epg imports
from source import sources

# get logging object
log = logging.getLogger('epg')

class Server(object):
    """
    Server class for the epg.
    """
    def __init__(self, dbfile):

        log.info('start epg server with database %s', dbfile)

        # create the db and register objects

        db = Database(dbfile)
        db.register_object_type_attrs("channel",
            tuner_id   = (list, ATTR_SIMPLE),
            name = (unicode, ATTR_SEARCHABLE),
            long_name  = (unicode, ATTR_SEARCHABLE),
        )
        db.register_object_type_attrs("program",
            [ ("start", "stop") ],
            title = (unicode, ATTR_KEYWORDS),
            desc = (unicode, ATTR_KEYWORDS),
            start = (int, ATTR_SEARCHABLE),
            stop = (int, ATTR_SEARCHABLE),
            episode = (unicode, ATTR_SIMPLE),
            subtitle = (unicode, ATTR_SIMPLE),
            genre = (unicode, ATTR_SIMPLE),
            date = (int, ATTR_SEARCHABLE),
            rating = (dict, ATTR_SIMPLE)
        )

        self._clients = []
        self._db = db
        self._setup_internal_variables()
        self._rpc_server = []

        # start unix socket rpc connection
        s = kaa.rpc.Server('epg')
        s.signals['client_connected'].connect(self.client_connected)
        s.connect(self)
        self._rpc_server.append(s)


    # -------------------------------------------------------------------------
    # kaa.rpc interface called by kaa.epg.Client
    # -------------------------------------------------------------------------

    @kaa.rpc.expose('server.start')
    def connect_to_network(self, address, auth_secret):
        """
        Start a network connection (tcp) with the given address and secret.
        The function will return addr/port so you can set port to 0 to let the
        system choose one.
        """
        host, port = address.split(':', 1)
        s = kaa.rpc.Server((host, int(port)), auth_secret = auth_secret)
        s.signals['client_connected'].connect(self.client_connected)
        s.connect(self)
        self._rpc_server.append(s)
        host, port = s.socket.getsockname()
        log.info('listening on address %s:%s', host, port)
        return host, port


    @kaa.rpc.expose('guide.update')
    def update(self, backend, *args, **kwargs):
        """
        Start epg update calling the source_* files.
        """
        if not sources.has_key(backend):
            raise ValueError, "No such update backend '%s'" % backend
        log.info('update backend %s', backend)
        return sources[backend].update(self, *args, **kwargs)


    @kaa.rpc.expose('guide.query')
    def query(self, channel=None, **kwargs):
        if channel:
            if isinstance(channel, (list, tuple)):
                kwargs["parent"] = [("channel", x) for x in channel]
            else:
                kwargs["parent"] = "channel", channel
        return [ dict(row) for row in self._db.query(**kwargs) ]


    # -------------------------------------------------------------------------
    # kaa.rpc client handling
    # -------------------------------------------------------------------------

    def client_connected(self, client):
        """
        Connect a new client to the server.
        """
        info = self._channel_list, self._max_program_length, self._num_programs
        client.rpc('guide.update', info)
        client.signals['closed'].connect(self.client_closed, client)
        self._clients.append(client)


    def client_closed(self, client):
        """
        Callback when a client disconnects.
        """
        log.warning('disconnect client %s', client)
        self._clients.remove(client)


    # -------------------------------------------------------------------------
    # functions called by source_* modules
    # -------------------------------------------------------------------------

    @kaa.notifier.execute_in_mainloop()
    def guide_changed(self):
        """
        Guide changed by source, commit changes to database and notify clients.
        """
        log.info('commit database changes')
        self._db.commit()
        self._setup_internal_variables()
        info = self._channel_list, self._max_program_length, self._num_programs
        for client in self._clients:
            log.info('update client %s', client)
            client.rpc('guide.update', info)


    def add_channel(self, tuner_id, name, long_name):
        """
        This method requires at least one of tuner_id, name, long_name.
        Depending on the source (various XMLTV sources, Zap2it, etc.) not all
        of the information we would like is available.  Also, channels are
        perceived differently around the world and handled differently by
        differnent systems (DVB, analog TV).

        Following the KISS philosophy (Keep It Simple Stupid) we can follow some
        simple rules.

        The most important field here is name.  If there's no name
        we make it based on tuner_id or long_name.  If there's no long_name we
        base that on name or tuner_id.  If there's no tuner_id it does
        not matter because we will then always have a value for name.
        If there is a tuner_id then it will assist programs using kaa.epg to
        match real channels and EPG data.
        """

        if type(tuner_id) != ListType and tuner_id:
            tuner_id = [ tuner_id ]

        # require at least one field
        if not tuner_id and not name and not long_name:
            log.error('need at least one field to add a channel')
            return None

        if not name:
            # then there must be one of the others
            if tuner_id:
                name = tuner_id[0]
            else:
                name = long_name

        if not long_name:
            # then there must be one of the others
            if name:
                long_name = name
            elif tuner_id:
                long_name = tuner_id[0]

        if not tuner_id:
            tuner_id = [ name ]


        c2 = self._db.query(type = "channel", name = name)
        if len(c2):
            c2 = c2[0]

            for t in tuner_id:
                if t not in c2["tuner_id"]:
                    if t in self._tuner_ids:
                        log.warning('not adding tuner_id %s for channel %s - '+\
                            'it is claimed by another channel', t, name)
                    else:
                        # only add this id if it's not already there and not
                        # claimed by another channel
                        c2["tuner_id"].append(t)
                        self._tuner_ids.append(t)

            # TODO: if everything is the same do not update
            log.info('update channel %s', name)
            self._db.update_object(("channel", c2["id"]),
                                   tuner_id = c2["tuner_id"],
                                   long_name = long_name)
            return c2["id"]

        for t in tuner_id:
            if t in self._tuner_ids:
                log.warning('not adding tuner_id %s for channel %s - it is '+\
                            'claimed by another channel', t, name)
                tuner_id.remove(t)
            else:
                self._tuner_ids.append(t)

        log.info('add channel %s %s %s', tuner_id, name, long_name)
        o = self._db.add_object("channel", tuner_id = tuner_id, name = name,
                                long_name = long_name)
        return o["id"]


    def add_program(self, channel_db_id, start, stop, title, **attributes):
        """
        Add a program to the db. This could cause removing older programs
        overlapping.
        """
        start = int(start)
        stop = int(stop)

        # Find all programs that have a start or stop during this program
        s1 = self._db.query(parent = ("channel", channel_db_id), type = "program",
                            start = QExpr("range", (start, stop-1)))
        s2 = self._db.query(parent = ("channel", channel_db_id), type = "program",
                            stop = QExpr("range", (start+1, stop)))

        # In a perfect world this program is already in the db and is in s1 and
        # s2 and both lists have a length of 1
        if len(s1) == len(s2) == 1 and start == s1[0]['start'] == s2[0]['start'] and \
               stop == s1[0]['stop'] == s2[0]['stop']:
            # yes, update object if it is different
            prg = s1[0]
            if prg['title'] != title:
                log.info('update %s', title)
                self._db.update_object(("program", prg["id"]), start = start,
                                       stop = stop, title = title, **attributes)
            return prg["id"]

        removed = []
        for r in s1 + s2:
            # OK, something is wrong here with some overlapping. Either the source
            # of the guide has no overlap detection or the schedule has changed.
            # Anyway, the best we can do now is to remove everything that is in our
            # conflict
            if r['id'] in removed:
                continue
            log.info('remove %s', r['title'])
            self._db.delete_object(("program", r['id']))
            removed.append(r['id'])

        # Now add the new program
        log.info('adding program: %s', title)
        o = self._db.add_object("program", parent = ("channel", channel_db_id),
                                start = start, stop = stop, title = title,
                                **attributes)

        if stop - start > self._max_program_length:
            self._max_program_length = stop = start
        return o["id"]


    # -------------------------------------------------------------------------
    # internal functions
    # -------------------------------------------------------------------------

    def _setup_internal_variables(self):
        """
        Load some basic information from the db.
        """
        self._max_program_length = self._num_programs = 0
        q = "SELECT stop-start AS length FROM objects_program ORDER BY length DESC LIMIT 1"
        res = self._db._db_query(q)
        if len(res):
            self._max_program_length = res[0][0]

        res = self._db._db_query("SELECT count(*) FROM objects_program")
        if len(res):
            self._num_programs = res[0][0]

        self._tuner_ids = []
        channels = self._db.query(type = "channel")
        for c in channels:
            for t in c["tuner_id"]:
                if t in self._tuner_ids:
                    log.warning('loading channel %s with tuner_id %s '+\
                                'allready claimed by another channel',
                                c["name"], t)
                else:
                    self._tuner_ids.append(t)

        # get channel list to be passed to a client on connect / update
        self._channel_list = [ (r['id'], r['tuner_id'], r['name'], r['long_name']) \
                               for r in self._db.query(type="channel") ]
