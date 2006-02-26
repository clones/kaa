import libxml2, sys, time, os, weakref, logging
from kaa.base.db import *
from kaa.base import ipc
from kaa.notifier import Signal

__all__ = ['GuideServer']

log = logging.getLogger('epg')

# TODO: merge updates when processing instead of wipe.

class GuideServer(object):
    def __init__(self, socket, dbfile = "/tmp/GuideServer.db", auth_secret = None,
                 log_file = "/tmp/GuideServer.log", log_level = logging.INFO):

        # setup logger
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
            name = (unicode, ATTR_SEARCHABLE),
            station = (unicode, ATTR_SEARCHABLE),
            channel = (int, ATTR_SEARCHABLE),
            channel_id = (unicode, ATTR_SIMPLE)
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


    def _load(self):
        self._max_program_length = self._num_programs = 0
        q = "SELECT stop-start AS length FROM objects_program ORDER BY length DESC LIMIT 1"
        res = self.get_db()._db_query(q)
        if len(res):
            self._max_program_length = res[0][0]

        res = self.get_db()._db_query("SELECT count(*) FROM objects_program")
        if len(res):
            self._num_programs = res[0][0]


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
        try:
            exec('import source_%s as backend' % backend)
        except ImportError:
            raise ValueError, "No such update backend '%s'" % backend

        self._wipe()
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
            print "\nProcessed in %.02f seconds." % (time.time()-update_start_time)


    def _wipe(self):
        t0=time.time()
        self._db.delete_by_query()
        self._channel_id_to_db_id = {}


    def _add_channel_to_db(self, id, channel, station, name):
        log.debug("%s ^ %s ^ %s ^ %s", id, channel, station, name)
        o = self._db.add_object("channel", 
                                channel = channel,
                                station = station,
                                name = name,
                                channel_id = id)
        return o["id"]


    def _add_program_to_db(self, channel_id, start, stop, title, desc):
        o = self._db.add_object("program", 
                                parent = ("channel", channel_id),
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

        log.debug("clients: %s", len(_server._clients))
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
    
    _server = GuideServer("epg", dbfile=sys.argv[3], log_file=str(sys.argv[1]), 
                          log_level=int(sys.argv[2]))

    garbage_collect()
    autoshutdown()
    loop()
