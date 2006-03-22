import libxml2, sys, time, os, weakref, cPickle
import logging

from kaa import ipc, db
from kaa.notifier import Signal
from server import *
from channel import *
from program import *

__all__ = ['Client']

log = logging.getLogger()


class Client(object):
    def __init__(self, server_or_socket, auth_secret = None):
        self.connected = True
        self._ipc = ipc.IPCClient(server_or_socket, auth_secret = auth_secret)
        self._server = self._ipc.get_object("guide")

        self.signals = {
            "updated": Signal(),
            "update_progress": Signal(),
            "disconnected": Signal()
        }

        self._load()
        self._ipc.signals["closed"].connect(self._disconnected)
        self._server.signals["updated"].connect(self._updated)
        self._server.signals["update_progress"].connect(self.signals["update_progress"].emit)

    def _disconnected(self):
        self.connected = False
        self.signals["disconnected"].emit()

        
    def _updated(self):
        self._load()
        self.signals["updated"].emit()


    def _load(self):
        self._channels_by_name = {}
        self._channels_by_db_id = {}
        self._channels_by_tuner_id = {}
        self._channels_list = []
        data = self._server.query(type="channel", __ipc_noproxy_result = True)
        for row in db.iter_raw_data(data, ("id", "tuner_id", "name", "long_name")):
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

        self._max_program_length = self._server.get_max_program_length()
        self._num_programs = self._server.get_num_programs()


    def _program_rows_to_objects(self, query_data):
        cols = "parent_id", "start", "stop", "title", "desc", "id"#, "ratings"
        results = []
        for row in db.iter_raw_data(query_data, cols):
            if row[0] not in self._channels_by_db_id:
                continue
            channel = self._channels_by_db_id[row[0]]
            program = Program(channel, row[1], row[2], row[3], row[4])
            program.db_id = row[5]
            results.append(program)
        return results


    def search(self, **kwargs):
        if not self.connected:
            return []

        if "channel" in kwargs:
            ch = kwargs["channel"]
            if type(ch) == Channel:
                kwargs["channel"] = ch.db_id
            elif type(ch) == tuple and len(ch) == 2:
                kwargs["channel"] = db.QExpr("range", (ch[0].db_id, ch[1].db_id))
            else:
                raise ValueError, "channel must be Channel object or tuple of 2 Channel objects"

        if "time" in kwargs:
            if type(kwargs["time"]) in (int, float, long):
                # Find all programs currently playing at the given time.  We
                # add 1 second as a heuristic to prevent duplicates if the
                # given time occurs on a boundary between 2 programs.
                start, stop = kwargs["time"] + 1, kwargs["time"] + 1
            else:
                start, stop = kwargs["time"]

            max = self.get_max_program_length()
            kwargs["start"] = db.QExpr("range", (int(start) - max, int(stop)))
            kwargs["stop"] = db.QExpr(">=", int(start))
            del kwargs["time"]

        kwargs["type"] = "program"
        data = self._server.query(__ipc_noproxy_result = True, **kwargs)
        if not data[1]:
            return []
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
        if name not in self._channels_by_name:
            return None
        return self._channels_by_name[name]

    def get_channel_by_db_id(self, db_id):
        if db_id not in self._channels_by_db_id:
            return None
        return self._channels_by_db_id[db_id]

    def get_channel_by_tuner_id(self, tuner_id):
        if tuner_id not in self._channels_by_tuner_id:
            return None
        return self._channels_by_tuner_id[tuner_id]

    def get_max_program_length(self):
        return self._max_program_length

    def get_num_programs(self):
        return self._num_programs

    def get_channels(self):
        return self._channels_list

    def update(self, *args, **kwargs):
        if not self.connected:
            return False
        
        # updated signal will fire when this call completes.
        kwargs["__ipc_oneway"] = True
        kwargs["__ipc_noproxy_args"] = True
        self._server.update(*args, **kwargs)
