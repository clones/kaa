# -*- coding: iso-8859-1 -*-
# -----------------------------------------------------------------------------
# client.py - client part of the epg
# -----------------------------------------------------------------------------
# $Id$
# -----------------------------------------------------------------------------
# kaa.epg - EPG Database
# Copyright (C) 2004-2005 Jason Tackaberry, Dirk Meyer, Rob Shortt
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

__all__ = ['Client']

# python imports
import logging

# kaa imports
import kaa.db
import kaa.rpc
from kaa.notifier import Signal, OneShotTimer, execute_in_timer

# kaa.epg imports
from channel import Channel
from program import Program

# get logging object
log = logging.getLogger('epg')

DISCONNECTED, CONNECTING, CONNECTED = range(3)

class Client(object):
    """
    EPG client class to access the epg on server side.
    """
    def __init__(self, server_or_socket, auth_secret = ''):
        self.status = CONNECTING
        self.server = kaa.rpc.Client(server_or_socket, auth_secret = auth_secret)
        self.server.connect(self)
        
        self._channels_list = []
        self.signals = {
            "updated": Signal(),
            "connected": Signal(),
            "disconnected": Signal()
        }

        self._channels_by_name = {}
        self._channels_by_db_id = {}
        self._channels_by_tuner_id = {}
        self._channels_list = []

        self.server.signals['closed'].connect_weak(self._handle_disconnected)


    def _handle_disconnected(self):
        """
        Signal callback when server disconnects.
        """
        log.error('kaa.epg client disconnected')
        self.status = DISCONNECTED
        self.signals["disconnected"].emit()
        log.info('delete server link')
        del self.server


    @kaa.rpc.expose('guide.update')
    def _handle_guide_update(self, (epgdata, max_program_length, num_programs)):
        """
        (re)load some static information
        """
        self._channels_by_name = {}
        self._channels_by_db_id = {}
        self._channels_by_tuner_id = {}
        self._channels_list = []

        for row in epgdata:
            db_id, tuner_id, name, long_name = row
            chan = Channel(tuner_id, name, long_name, self)
            chan.db_id = db_id
            self._channels_by_name[name] = chan
            self._channels_by_db_id[db_id] = chan
            for t in tuner_id:
                if self._channels_by_tuner_id.has_key(t):
                    log.warning('loading channel %s with tuner_id %s '+\
                                'allready claimed by channel %s', 
                                chan.name, t, 
                                self._channels_by_tuner_id[t].name)
                else:
                    self._channels_by_tuner_id[t] = chan
            self._channels_list.append(chan)

        # get attributes from server and store local
        self._max_program_length = max_program_length
        self._num_programs = num_programs

        if self.status == CONNECTING:
            self.status = CONNECTED
            self.signals["connected"].emit()
        self.signals["updated"].emit()

        
    def _program_rows_to_objects(self, query_data, callback=None):
        """
        Convert raw search result data from the server into python objects.
        """
        results = []
        for row in query_data:
            if row[0] not in self._channels_by_db_id:
                continue
            channel = self._channels_by_db_id[row[0]]
            program = Program(channel, *row[2:])
            results.append(program)
        if callback:
            callback(results)
        return results


    def search(self, callback=None, **kwargs):
        """
        Search the db. This will call the search function on server side using
        kaa.ipc. Notice: this will call kaa.notifier.step() until the result
        arrives.
        """
        if self.status == DISCONNECTED:
            return []

        if "channel" in kwargs:
            ch = kwargs["channel"]
            if type(ch) == Channel:
                kwargs["channel"] = ch.db_id
            elif type(ch) == tuple and len(ch) == 2:
                kwargs["channel"] = kaa.db.QExpr("range", (ch[0].db_id, ch[1].db_id))
            else:
                # FIXME: this is ugly. Why not a longer list?
                raise ValueError, "channel must be Channel object"

        if "time" in kwargs:
            if type(kwargs["time"]) in (int, float, long):
                # Find all programs currently playing at the given time.  We
                # add 1 second as a heuristic to prevent duplicates if the
                # given time occurs on a boundary between 2 programs.
                start, stop = kwargs["time"] + 1, kwargs["time"] + 1
            else:
                start, stop = kwargs["time"]

            max = self._max_program_length
            kwargs["start"] = kaa.db.QExpr("range", (int(start) - max, int(stop)))
            kwargs["stop"] = kaa.db.QExpr(">=", int(start))
            del kwargs["time"]

        if callback:
            rpc = self.server.rpc('guide.query', self._program_rows_to_objects, callback)
            rpc(type='program', **kwargs)
            return None
        data = self.server.rpc('guide.query', 'blocking')(type='program', **kwargs)
        return self._program_rows_to_objects(data)


    def new_channel(self, tuner_id=None, name=None, long_name=None):
        """
        Returns a channel object that is not associated with the EPG.
        This is useful for clients that have channels that do not appear
        in the EPG but wish to handle them anyway.
        """

        # require at least one field
        if not tuner_id and not name and not long_name:
            log.error('need at least one field to create a channel')
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

        return Channel(tuner_id, name, long_name, epg=None)


    def get_channel(self, name):
        """
        Get channel by name.
        """
        if name not in self._channels_by_name:
            return None
        return self._channels_by_name[name]


    def get_channel_by_db_id(self, db_id):
        """
        Get channel by database id.
        """
        if db_id not in self._channels_by_db_id:
            return None
        return self._channels_by_db_id[db_id]


    def get_channel_by_tuner_id(self, tuner_id):
        """
        Get channel by tuner id.
        """
        if tuner_id not in self._channels_by_tuner_id:
            return None
        return self._channels_by_tuner_id[tuner_id]


    def get_max_program_length(self):
        """
        Get maximum program length
        """
        return self._max_program_length


    def get_num_programs(self):
        """
        Get number of programs in the db.
        """
        return self._num_programs


    def get_channels(self):
        """
        Get all channels
        """
        return self._channels_list


    def update(self, *args, **kwargs):
        """
        Update the database. This will call the update function in the server
        and the server needs to be configured for that.
        """
        if self.status == DISCONNECTED:
            return False
        self.server.rpc('guide.update')(*args, **kwargs)
