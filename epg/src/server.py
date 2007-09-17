# -*- coding: iso-8859-1 -*-
# -----------------------------------------------------------------------------
# server.py - server part of the epg
# -----------------------------------------------------------------------------
# $Id$
# -----------------------------------------------------------------------------
# kaa.epg - EPG Database
# Copyright (C) 2004-2007 Jason Tackaberry, Dirk Meyer, Rob Shortt
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

__all__ = [ 'Server']

# python imports
import logging
import time
from types import ListType
import threading

# kaa imports
from kaa.db import *
import kaa.rpc

import kaa.notifier

# kaa.epg imports
from config import config
from sources import *

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
        db.register_inverted_index('keywords', min = 2, max = 30)
        db.register_object_type_attrs("channel",
            tuner_id   = (list, ATTR_SIMPLE),
            name = (unicode, ATTR_SEARCHABLE),
            long_name  = (unicode, ATTR_SEARCHABLE),
        )
        db.register_object_type_attrs("program",
            [ ("start", "stop") ],
            title = (unicode, ATTR_SEARCHABLE | ATTR_INVERTED_INDEX, 'keywords'),
            desc = (unicode, ATTR_SEARCHABLE | ATTR_INVERTED_INDEX, 'keywords'),
            start = (int, ATTR_SEARCHABLE),
            stop = (int, ATTR_SEARCHABLE),
            episode = (unicode, ATTR_SIMPLE),
            subtitle = (unicode, ATTR_SIMPLE),
            genre = (unicode, ATTR_SEARCHABLE),
            category = (unicode, ATTR_SEARCHABLE),  
            date = (int, ATTR_SEARCHABLE),
            rating = (dict, ATTR_SIMPLE)
        )

        self._clients = []
        self._db = db
        self._rpc_server = []
        
        # Members for job queue.
        self._jobs = []
        self._jobs_lock = threading.Lock()
        self._jobs_timer = kaa.notifier.WeakTimer(self._handle_jobs)

        # initial sync
        self.sync()

        # start unix socket rpc connection
        s = kaa.rpc.Server('epg')
        s.signals['client_connected'].connect(self.client_connected)
        s.connect(self)
        self._rpc_server.append(s)


    def sync(self):
        """
        Sync database. The guide may changed by source, commit changes to
        database and notify clients. Load some basic settings from the db.
        """
        # Prune obsolete programs from database.
        expired_time = time.time() - config.expired_days * 60 * 60 * 24
        count = self._db.delete_by_query(type = "program", stop = QExpr('<', expired_time))
        if count:
            log.info('Deleted %d expired programs from database' % count)
        self._db.commit()

        # Load some basic information from the db.
        self._max_program_length = self._num_programs = 0
        q = 'SELECT stop-start AS length FROM objects_program ' + \
            'ORDER BY length DESC LIMIT 1'
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

        info = self._channel_list, self._max_program_length, self._num_programs
        for client in self._clients:
            log.info('update client %s', client)
            client.rpc('guide.update', info)

        log.info('Database commit; %d programs in db' % self._num_programs)


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
    @kaa.notifier.yield_execution()
    def update(self, backend = None, *args, **kwargs):
        """
        Start epg update calling the source_* files.  If backend is specified,
        only call update() from that specific backend.  Otherwise call update
        on all enabled backends in the 'sources' config value.
        """
        if backend:
            backends = [backend]
        elif config.sources:
            backends = config.sources.replace(' ', '').split(',')
        else:
            backends = []

        for backend in backends[:]:
            if backend not in sources:
                log.error("No such update backend '%s'" % backend)
                backends.remove(backend)
                continue

            log.info('Updating backend %s', backend)
            # Backend's update() must be threaded, and so will return an
            # InProgress object that we now yield.
            yield sources[backend].update(self, *args, **kwargs)

        if not backends:
            log.warning('No valid backends specified for update.')
            return

        self.sync()


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
        log.info('Client disconnected: %s', client)
        self._clients.remove(client)


    # -------------------------------------------------------------------------
    # functions called by source_* modules
    # -------------------------------------------------------------------------

    @kaa.notifier.execute_in_mainloop()
    def add_channel(self, tuner_id, name, long_name):
        """
        This method requires at least one of tuner_id, name,
        long_name.  Depending on the source (various XMLTV sources,
        Zap2it, etc.) not all of the information we would like is
        available.  Also, channels are perceived differently around
        the world and handled differently by differnent systems (DVB,
        analog TV).

        Following the KISS philosophy (Keep It Simple Stupid) we can
        follow some simple rules.

        The most important field here is name.  If there's no name we
        make it based on tuner_id or long_name.  If there's no
        long_name we base that on name or tuner_id.  If there's no
        tuner_id it does not matter because we will then always have a
        value for name.  If there is a tuner_id then it will assist
        programs using kaa.epg to match real channels and EPG data.
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
                            'it is claimed by another channel (%s)', t, name, self._tuner_ids[t])
                    else:
                        # only add this id if it's not already there and not
                        # claimed by another channel
                        c2["tuner_id"].append(t)
                        self._tuner_ids.append(t)

            # TODO: if everything is the same do not update
            log.debug('Updating channel %s', name)
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

        log.debug('Adding channel %s %s %s', tuner_id, name, long_name)
        o = self._db.add_object("channel", tuner_id = tuner_id, name = name,
                                long_name = long_name)
        return o["id"]


    def _handle_jobs(self):
        """
        Handle waiting add_program jobs.
        """
        t0 = time.time()
        self._jobs_lock.acquire(False)
        while self._jobs:
            if time.time() - t0 > 0.05:
                # time to return to the main loop
                return True
            args = self._jobs.pop(0)
            self.add_program(*args[:-1], **args[-1])

        self._jobs_lock.release()
        return False


    def add_program(self, channel_db_id, start, stop, title, **attributes):
        """
        Add a program to the db. This could cause removing older programs
        overlapping.
        """
        if not kaa.notifier.is_mainthread():
            self._jobs.append((channel_db_id, start, stop, title, attributes))
            if len(self._jobs) == 1:
                # Job added to (probably) empty queue, begin timer to handle jobs
                # If timer is already running, this does nothing.  Timers are
                # implicitly called from the main loop.
                self._jobs_timer.start(0.001)
            elif len(self._jobs) > 100:
                # too many jobs pending, wait before adding new
                while len(self._jobs) > 30:
                    time.sleep(0.1)
            return
        
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
                log.debug('Updating existing program %s (channel db id=%d, start=%d, stop=%d)', 
                          title, channel_db_id, start, stop)
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
            log.debug('Removing conflicting program %s (channel db id=%d, start=%d, stop=%d)', 
                      r['title'], channel_db_id, r['start'], r['stop'])
            self._db.delete_object(("program", r['id']))
            removed.append(r['id'])

        # Now add the new program
        log.debug('Adding program %s (channel db id=%d, start=%d, stop=%d)', 
                  title, channel_db_id, start, stop)
        o = self._db.add_object("program", parent = ("channel", channel_db_id),
                                start = start, stop = stop, title = title,
                                **attributes)

        if stop - start > self._max_program_length:
            self._max_program_length = stop = start
        return o["id"]


    def add_program_wait(self):
        """
        Wait until add_program is finished. This function can only be called
        from a thread.
        """
        if kaa.notifier.is_mainthread():
            raise RuntimeError('add_program_wait not called by thread')

        # Jobs lock is held as long as the jobs handler timer is running.
        self._jobs_lock.acquire()
        self._jobs_lock.release()
