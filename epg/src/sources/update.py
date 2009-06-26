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

__all__ = [ 'update', 'sources' ]

# python imports
import logging
import time
from types import ListType
import os
import kaa.utils

# kaa imports
import kaa
from kaa.db import *

# kaa.epg imports
from config import config

# get logging object
log = logging.getLogger('epg.update')

sources = {}

# TODO: Support for egg.
for c in kaa.utils.get_plugins(os.path.dirname(__file__)):
    if not c.startswith('config_'):
        continue
    name = c[7:]
    try:
        exec('import %s as module' % name)
        exec('import %s as cfg' % c)
    except ImportError:
        continue
    sources[name] = module
    config.add_variable(name, cfg.config)

class Updater(object):
    """
    """
    def __init__(self, db):
        self._db = db
        # Members for job queue.
        self._jobs = []
        # Tuner ids: id -> name
        self._tuner_ids = {}
        for c in self._db.query(type = "channel"):
            for t in c["tuner_id"]:
                if t in self._tuner_ids:
                    log.warning('duplicate tuner id %s', t)
                else:
                    self._tuner_ids[t] = c['name']


    @kaa.coroutine()
    def update(self, backend = None, *args, **kwargs):
        """
        Start epg update calling the source_* files.  If backend is specified,
        only call update() from that specific backend.  Otherwise call update
        on all enabled backends in the 'sources' config value.
        """
        # Prune obsolete programs from database.
        expired_time = time.time() - config.expired_days * 60 * 60 * 24
        count = self._db.delete_by_query(type = "program", stop = QExpr('<', expired_time))
        if count:
            log.info('Deleted %d expired programs from database' % count)
        # Vacuum database, which removes keywords with count=0
        log.info('Vacuuming database')
        self._db.vacuum()

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
            # Backend's update() MUST return an InProgress object
            try:
                # The yield may crash on Python 2.5 using throw
                # An error message will not be visible for 2.4
                yield sources[backend].update(self, *args, **kwargs)
            except (KeyboardInterrupt, SystemExit):
                sys.exit(0)
            except Exception, e:
                log.exception('Backend %s failed' % backend)
            self.sync()

        if not backends:
            log.warning('No valid backends specified for update.')
            return
        log.info('update complete')

        self._db.commit()

        # Load some statistics
        res = self._db._db_query("SELECT count(*) FROM objects_program")
        num_programs = res[0][0] if len(res) else 0
        log.info('Database commit; %d programs in db' % num_programs)

    # -------------------------------------------------------------------------
    # functions called by source_* modules
    # -------------------------------------------------------------------------

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
            name = tuner_id[0] if tuner_id else long_name
        if not long_name:
            # then there must be one of the others
            long_name = name if name else tuner_id[0]
        if not tuner_id:
            tuner_id = [ name ]

        for t in tuner_id:
            if t in self._tuner_ids and self._tuner_ids[t] != name:
                # The tuner id for this new channel is mapped to another one, so
                # remove the old one.
                channel = self._db.query(type='channel', name=self._tuner_ids[t])[0]
                log.warning('Reassigning tuner id %s from channel %s (%s) to %s (%s)',
                            t, channel['name'], channel['long_name'], name, long_name)
                channel['tuner_id'].remove(t)
                self._db.update(('channel', channel['id']), tuner_id=channel['tuner_id'])
                # TODO: if channel now has no tuner ids, and after processing the update
                # has no programs, we can remove it.
            self._tuner_ids[t] = name

        channel = self._db.query(type='channel', name=name)
        if channel:
            # Channel with this name already in database, so update it.
            channel = channel[0]
            db_tuner_ids = set(channel['tuner_id'] + tuner_id)
            if set(channel['tuner_id']) != db_tuner_ids or channel['long_name'] != long_name:
                # Either tuner id(s) or long name has changed, so update db.
                log.debug('Updating channel %s %s (%s)', db_tuner_ids, name, long_name)
                self._db.update(('channel', channel['id']), tuner_id=list(db_tuner_ids),
                                name=name, long_name=long_name)
            return channel['id']

        # New channel not in db, so add new object.
        log.debug('Adding channel %s %s (%s)', tuner_id, name, long_name)
        return self._db.add('channel', tuner_id=tuner_id, name=name, long_name=long_name)['id']


    def sync(self):
        """
        Handle waiting add_program jobs.
        """
        t0 = time.time()
        while self._jobs:
            channel_db_id, start, stop, title, attributes = self._jobs.pop(0)
            # Find all programs that have a start or stop during this program
            # TODO: the two queries take about 0.001 seconds which is too much
            s1 = self._db.query(parent = ("channel", channel_db_id), type = "program",
                                start = QExpr("range", (start, stop-1)))
            s2 = self._db.query(parent = ("channel", channel_db_id), type = "program",
                                stop = QExpr("range", (start+1, stop)))
            # In a perfect world this program is already in the db and is in s1 and
            # s2 and both lists have a length of 1
            if len(s1) == len(s2) == 1 and start == s1[0]['start'] == s2[0]['start'] and \
                   stop == s1[0]['stop'] == s2[0]['stop']:
                # yes, update object if it is different
                current = s1[0]
                if current['title'] != title:
                    log.debug('Updating existing program %s (channel db id=%d, start=%d, stop=%d)',
                              title, channel_db_id, start, stop)
                    self._db.update(("program", current["id"]), start = start,
                                    stop = stop, title = title, **attributes)
                continue
            # Check for overlapping entries
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
                self._db.delete(("program", r['id']))
                removed.append(r['id'])
            # Add the new program
            log.debug('Adding program %s (channel db id=%d, start=%d, stop=%d)',
                title, channel_db_id, start, stop)
            self._db.add("program", parent = ("channel", channel_db_id),
                         start = start, stop = stop, title = title, **attributes)
        self._db.commit()
        log.info('db commit took %0.3f secs', (time.time() - t0))
        return False

    def add_program(self, channel_db_id, start, stop, title, **attributes):
        """
        Add a program to the db. This could cause removing older programs
        overlapping. This is called by the source update thread.
        """
        self._jobs.append((channel_db_id, int(start), int(stop), title, attributes))
        if len(self._jobs) > 5000:
            self.sync()


def update(db, backend = None, *args, **kwargs):
    return Updater(db).update(backend, *args, **kwargs)
