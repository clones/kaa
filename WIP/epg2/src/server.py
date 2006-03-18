import libxml2, sys, time, os, weakref, logging
from types import ListType

from kaa.db import *
from kaa import ipc
from kaa.notifier import Signal

__all__ = ['DEFAULT_EPG_PORT', 'GuideServer']

DEFAULT_EPG_PORT = 4132

log = logging.getLogger('epg')

# TODO: merge updates when processing instead of wipe.

class GuideServer(object):
    def __init__(self, socket, address = None, dbfile = "/tmp/GuideServer.db", 
                 auth_secret = None, log_file = "/tmp/GuideServer.log", 
                 log_level = logging.INFO):

        # setup logger
        # TODO: get a better format!  half of my screen is taken up before getting
        #       to the log message.  A better time format would help, ie:
        #       '%Y%m%d %H:%M:%S'
        f = logging.Formatter('%(asctime)s %(levelname)-8s [%(name)6s] '+\
                              '%(filename)s %(lineno)s: '+\
                              '%(message)s')
        handler = logging.FileHandler(log_file)
        handler.setFormatter(f)
        logging.getLogger().addHandler(handler)

        # setup log
        logging.getLogger().setLevel(log_level)
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
            date = (int, ATTR_SEARCHABLE),
            start = (int, ATTR_SEARCHABLE),
            stop = (int, ATTR_SEARCHABLE),
            ratings = (dict, ATTR_SIMPLE)
        )

        self.signals = {
            "updated": Signal(),
            "update_progress": Signal()
        }

        self._clients = []
        self._db = db
        self._load()
        
        self._ipc = ipc.IPCServer(socket, auth_secret = auth_secret)
        self._ipc.signals["client_connected"].connect_weak(self._client_connected)
        self._ipc.signals["client_closed"].connect_weak(self._client_closed)
        self._ipc.register_object(self, "guide")

        self._ipc_net = None
 
        if address and \
           address.split(':')[0] not in ['127.0.0.1', '0.0.0.0']:
            # listen on tcp port too
            if address.find(':') >= 0:
                host, port = address.split(':', 1)
            else:
                host = address
                port = DEFAULT_EPG_PORT

            self._ipc_net = ipc.IPCServer((host, int(port)), auth_secret = auth_secret)
            log.info('listening on address %s:%s', host, port)
            self._ipc_net.signals["client_connected"].connect_weak(self._client_connected)
            self._ipc_net.signals["client_closed"].connect_weak(self._client_closed)
            self._ipc_net.register_object(self, "guide")


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
        log.error('update')
        try:
            exec('import source_%s as backend' % backend)
        except ImportError:
            raise ValueError, "No such update backend '%s'" % backend

        # TODO: delte old programs
        # self._wipe()
        self.signals["update_progress"].connect_weak(self._update_progress, time.time())
        backend.update(self, *args, **kwargs)


    def _update_progress(self, cur, total, update_start_time):
        if total <= 0:
            # Processing something, but don't yet know how much
            n = 0
        else:
            n = int((cur / float(total)) * 50)

        # Temporary: output progress status to stdout.
        # sys.stdout.write("|%51s| %d / %d\r" % (("="*n + ">").ljust(51), cur, total))
        # sys.stdout.flush()

        if cur == total:
            self._db.commit()
            self._load()
            self.signals["updated"].emit()
            self.signals["update_progress"].disconnect(self._update_progress)
            log.info("Processed in %.02f seconds." % (time.time()-update_start_time))


    def _wipe(self):
        t0=time.time()
        self._db.delete_by_query()
        self._channel_id_to_db_id = {}


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


    def _add_program_to_db(self, channel_db_id, start, stop, title, desc):
        #log.debug('channel_db_id: "%s" start: "%s" title: "%s"', 
        #          channel_db_id, start, title)

        # TODO: check time range
        p2 = self._db.query(parent = ("channel", channel_db_id),
                            type = "program", start = start)

        if len(p2):
            # we have a program at this time
            p2 = p2[0]

            #log.debug('updating program: %s', p2["title"])
            # TODO: if everything is the same do not update
            self._db.update_object(("program", p2["id"]),
                                   start = start,
                                   stop = stop,
                                   title = title, 
                                   desc = desc)
            return p2["id"]

        # TODO: check title, see if it is a different program.  Also check
        #       if the program is the same but shifted times a bit
        else:
            #log.debug('adding program: %s', title)
            o = self._db.add_object("program", 
                                    parent = ("channel", channel_db_id),
                                    start = start,
                                    stop = stop, 
                                    title = title, 
                                    desc = desc, ratings = 42)

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


if __name__ == "__main__":
    # ARGS: log file, log level, db file

    # python imports
    import gc
    import sys
    
    # kaa imports
    from kaa.notifier import Timer, execute_in_timer, loop
    
    @execute_in_timer(Timer, 1)
    def garbage_collect():
        g = gc.collect()
        if g:
            log.debug('gc: deleted %s objects' % g)
        if gc.garbage:
            log.warning('gc: found %s garbage objects' % len(gc.garbage))
            for g in gc.garbage:
                log.warning(g)
        return True


    shutdown_timer = 5

    @execute_in_timer(Timer, 1)
    def autoshutdown():
        global shutdown_timer
        global _server

        #log.debug("clients: %s", len(_server._clients))
        if _server and len(_server._clients) > 0:
            shutdown_timer = 5
            return True
        shutdown_timer -= 1
        if shutdown_timer == 0:
            log.info('shutdown EPG server')
            sys.exit(0)
        return True
    
    try:
        # detach for parent using a new sesion
        os.setsid()
    except OSError:
        # looks like we are started from the shell
        # TODO: start some extra debug here and disable autoshutdown
        pass
    
    if len(sys.argv) < 5:
        address = None
    else:
        address=sys.argv[4]

    _server = GuideServer("epg", log_file=str(sys.argv[1]), 
                          log_level=int(sys.argv[2]), dbfile=sys.argv[3],
                          address=sys.argv[4])

    garbage_collect()
    autoshutdown()
    loop()
