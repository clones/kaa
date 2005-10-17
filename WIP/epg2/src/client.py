import libxml2, sys, time, os, weakref, cPickle
from kaa.base import ipc, db
from kaa.notifier import Signal
from server import *
from channel import *
from program import *

__all__ = ['GuideClient']


class GuideClient(object):
    def __init__(self, server_or_socket, auth_secret = None):
        if type(server_or_socket) == GuideServer:
            self._server = server_or_socket
            self._ipc = None
        else:
            self._ipc = ipc.IPCClient(server_or_socket, auth_secret = auth_secret)
            self._server = self._ipc.get_object("guide")

        self.signals = {
            "updated": Signal(),
            "update_progress": Signal()
        }
    
        self._load()
        self._server.signals["updated"].connect(self._updated)
        self._server.signals["update_progress"].connect(self.signals["update_progress"].emit)

    def _updated(self):
        self._load()
        self.signals["updated"].emit()


    def _load(self):
        self._channels_by_number = {}
        self._channels_by_id = {}
        self._channels_list = []
        data = self._server.query(type="channel", __ipc_copy_result = True)
        for row in db.iter_raw_data(data, ("id", "channel", "station", "name")):
            id, channel, station, name = row
            chan = Channel(channel, station, name, self)
            chan.id = id
            self._channels_by_number[channel] = chan
            self._channels_by_id[id] = chan
            self._channels_list.append(chan)

        self._max_program_length = self._server.get_max_program_length()
        self._num_programs = self._server.get_num_programs()


    def _program_rows_to_objects(self, query_data):
        cols = "parent_id", "start", "stop", "title", "desc"#, "ratings"
        results = []
        for row in db.iter_raw_data(query_data, cols):
            if row[0] not in self._channels_by_id:
                continue
            channel = self._channels_by_id[row[0]]
            program = Program(channel, row[1], row[2], row[3], row[4])
            results.append(program)
        return results


    def search(self, **kwargs):
        if "channel" in kwargs:
            ch = kwargs["channel"]
            if type(ch) == Channel:
                kwargs["channel"] = ch.id
            elif type(ch) == tuple and len(ch) == 2:
                kwargs["channel"] = db.QExpr("range", (ch[0].id, ch[1].id))
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
        data = self._server.query(__ipc_copy_result = True, **kwargs)
        if not data[1]:
            return []
        return self._program_rows_to_objects(data)


    def get_channel(self, key):
        if key not in self._channels_by_number:
            return None
        return self._channels_by_number[key]

    def get_channel_by_id(self, id):
        if id not in self._channels_by_id:
            return None
        return self._channels_by_id[id]

    def get_max_program_length(self):
        return self._max_program_length

    def get_num_programs(self):
        return self._num_programs

    def get_channels(self):
        return self._channels_list

    def update(self, *args, **kwargs):
        # updated signal will fire when this call completes.
        kwargs["__ipc_oneway"] = True
        self._server.update(*args, **kwargs)
