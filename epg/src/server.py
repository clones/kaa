import sys, time, os, weakref, logging
from types import ListType

from kaa.db import *
from kaa import ipc
from kaa.notifier import Signal

__all__ = [ 'Server']

log = logging.getLogger('epg')

from source import sources

class Server(object):
    def __init__(self, dbfile):

        log.info('start EPG server')
        log.info('using database in %s', dbfile)

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
            ratings = (dict, ATTR_SIMPLE)
        )

        self.signals = {
            "updated": Signal(),
            "update_progress": Signal()
        }

        self._clients = []
        self._db = db
        self._load()
        
        self._ipc = ipc.IPCServer('epg')
        self._ipc.signals["client_connected"].connect_weak(self._client_connected)
        self._ipc.signals["client_closed"].connect_weak(self._client_closed)
        self._ipc.register_object(self, "guide")

        self._ipc_net = None
            

    def connect_to_network(self, address, auth_secret=None):
        # listen on tcp port too
        host, port = address.split(':', 1)

        self._ipc_net = ipc.IPCServer((host, int(port)), auth_secret = auth_secret)
        log.info('listening on address %s:%s', host, port)
        self._ipc_net.signals["client_connected"].connect_weak(self._client_connected)
        self._ipc_net.signals["client_closed"].connect_weak(self._client_closed)
        self._ipc_net.register_object(self, "guide")
        return self._ipc_net.socket.getsockname()


    def _load(self):
        self._max_program_length = self._num_programs = 0
        q = "SELECT stop-start AS length FROM objects_program ORDER BY length DESC LIMIT 1"
        res = self.get_db()._db_query(q)
        if len(res):
            self._max_program_length = res[0][0]

        res = self.get_db()._db_query("SELECT count(*) FROM objects_program")
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


    def _client_connected(self, client):
        """
        Connect a new client to the server.
        """
        self._clients.append(client)


    def _client_closed(self, client):
        for signal in self.signals.values():
            for callback in signal:
                if ipc.get_ipc_from_proxy(callback) == client:
                    signal.disconnect(callback)

        for c in self._clients:
            if c == client:
                log.warning('disconnect client')
                self._clients.remove(c)


    def update(self, backend, *args, **kwargs):
        if not sources.has_key(backend):
            raise ValueError, "No such update backend '%s'" % backend
        log.info('update backend %s', backend)
        return sources[backend].update(self, *args, **kwargs)


    def _add_channel_to_db(self, tuner_id, name, long_name):
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

        log.info('add channel %s %s %s', tuner_id, name, long_name)
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

        o = self._db.add_object("channel", 
                                tuner_id = tuner_id,
                                name = name,
                                long_name = long_name)
        return o["id"]


    def _add_program_to_db(self, channel_db_id, start, stop, title, **attributes):
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


    def query(self, **kwargs):
        if "channel" in kwargs:
            if type(kwargs["channel"]) in (list, tuple):
                kwargs["parent"] = [("channel", x) for x in kwargs["channel"]]
            else:
                kwargs["parent"] = "channel", kwargs["channel"]
            del kwargs["channel"]

        for key in kwargs.copy():
            if key.startswith("__ipc_"):
                del kwargs[key]

        res = self._db.query_raw(**kwargs)
        return res


    def get_db(self):
        return self._db


    def get_max_program_length(self):
        return self._max_program_length


    def get_num_programs(self):
        return self._num_programs
