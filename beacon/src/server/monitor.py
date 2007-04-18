# -*- coding: iso-8859-1 -*-
# -----------------------------------------------------------------------------
# monitor.py - Monitor for changes in Beacon
# -----------------------------------------------------------------------------
# $Id$
#
# -----------------------------------------------------------------------------
# kaa.beacon.server - A virtual filesystem with metadata
# Copyright (C) 2006-2007 Dirk Meyer
#
# First Edition: Dirk Meyer <dischi@freevo.org>
# Maintainer:    Dirk Meyer <dischi@freevo.org>
#
# Please see the file AUTHORS for a complete list of authors.
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
#
# You should have received a copy of the GNU General Public License along
# with this program; if not, write to the Free Software Foundation, Inc.,
# 59 Temple Place, Suite 330, Boston, MA 02111-1307 USA
#
# -----------------------------------------------------------------------------


# python imports
import logging

# kaa imports
from kaa.weakref import weakref
from kaa.notifier import OneShotTimer, Timer, yield_execution, YieldContinue

# kaa.beacon imports
from kaa.beacon.item import Item

# kaa.beacon server imports
import parser

# get logging object
log = logging.getLogger('beacon.monitor')

class Master(object):
    """
    Master Monitor. This monitor will connect to the db and will call all
    monitors with the changes. This class will make sure they don't re-query
    all at once and have a small delay between them to keep the load down.
    """
    def __init__(self, db):
        self.monitors = []
        self.timer = Timer(self.check)
        db.signals['changed'].connect(self.changed)


    def connect(self, monitor):
        """
        Connect a new monitor.
        """
        self.monitors.append((weakref(monitor), [ False, [] ]))


    def changed(self, changes):
        """
        Database callback with changed ids.
        """
        if len(changes) == 1 and changes[0][0] == 'media':
            for m, c in self.monitors:
                c[0] = True
        for m, c in self.monitors:
            c[1].extend(changes)
        if not self.timer.active():
            self.timer.start(0.02)


    def check(self):
        """
        Timed callback to call the connected monitor update functions.
        """
        if not self.monitors:
            return False
        monitor, (force, changes) = self.monitors.pop(0)
        if monitor == None:
            return True
        if changes or force:
            monitor.check(changes)
        self.monitors.append((monitor, [ False, [] ]))
        return len(changes) > 0 or force


class Monitor(object):
    """
    Monitor query for changes and call the client.
    """

    _master = None

    def __init__(self, client, db, server, id, query):
        log.info('create new monitor %s' % id)
        self.id = id
        self._client = client
        self._server = server
        self._db = db
        self._query = query
        self._checking = False
        self._running = True
        self._check_changes = []
        self.items = self._db.query(**self._query)
        if not Monitor._master:
            Monitor._master = Master(db)
        Monitor._master.connect(self)
        if self.items and isinstance(self.items[0], Item):
            self._initial_scan()

        # FIXME: how to get updates on directories not monitored by
        # inotify? Maybe poll the dirs when we have a query with
        # dirname it it?


    def notify_client(self, *args, **kwargs):
        """
        Send notify rpc to client.
        """
        try:
            self._client.rpc('notify', self.id, *args, **kwargs)
        except IOError:
            pass


    def check(self, changes):
        """
        This function compares the last query result with the current db status
        and will inform the client when there is a change.
        """
        if not self._running:
            return True

        if self._checking:
            # Still checking. Question: What happens if new files are added
            # during scan? For one part, the changes here here the item changes
            # itself, so we would update the client all the time. So it is
            # better to wait here. Note: with inotify support this should not
            # happen often.
            self._check_changes.extend(changes)
            return True

        if self._check_changes:
            changes = self._check_changes + changes
            self._check_changes = []

        current = self._db.query(**self._query)

        # The query result length is different, this is a change
        if len(current) != len(self.items):
            log.info('monitor %s has changed', self.id)
            self.items = current
            self.notify_client('changed', True)
            return True

        # Same length and length is 0. No change here
        if len(current) == 0:
            return True

        # Same length, check for changes inside the items
        if isinstance(current[0], Item):
            small_changes = False
            for i in current:
                # We only compare the ids. If an item had no id before and
                # has now we can't detect it. But we only call this function
                # if we have a full scanned db. So an empty id also triggers
                # the update call.
                if not i._beacon_id:
                    log.info('monitor %s has changed', self.id)
                    self.items = current
                    self.notify_client('changed', True)
                    return True
                if not changes and i._beacon_id in changes:
                    small_changes = True
            if small_changes:
                # only small stuff
                log.info('monitor %s has changed', self.id)
                self.items = current
                self.notify_client('changed', False)
                return True
            return True

        # Same length and items are not type Item. This means they are strings
        # from 'attr' query.
        last = self.items[:]
        for c in current:
            if last.pop(0) != c:
                self.items = current
                self.notify_client('changed', True)
                return True
        return True


    @yield_execution(0.01)
    def _initial_scan(self):
        """
        Start scanning the current list of items if they need to be updated.
        With a full structure covered by inotify, there should be not changes.
        """
        self._checking = True
        changed = []

        c = 0
        for i in self.items[:]:
            c += 1
            if c > 20:
                # stop it and continue in the next step
                yield YieldContinue
            # TODO: maybe also check parents?
            if i._beacon_changed():
                changed.append(i)

        if not changed:
            # no changes but it was our first call. Tell the client that
            # everything is checked
            self.notify_client('checked')
            self._checking = False
            yield False

        if not changed:
            # no changes but send the 'changed' ipc to the client
            self.notify_client('changed', False)
            self._checking = False
            yield False

        for pos, item in enumerate(changed):
            self.notify_client('progress', pos+1, len(changed), item.url)
            parser.parse(self._db, item)
            yield YieldContinue
            if not self._running:
                break

        self._db.commit()

        # The client will update its query on this signal, so it should
        # be safe to do the same here. *cross*fingers*
        self.items = self._db.query(**self._query)
        # Do not send 'changed' signal here. The db was changed and the
        # master notification will do the rest. Just to make sure it will
        # happen, start a Timer
        if self._check_changes:
            # Set new check timer. This should not be needed, but just in
            # case :)
            OneShotTimer(self.check, []).start(0.5)
        self.notify_client('checked')
        self._checking = False
        yield False


    def stop(self):
        """
        Stop checking.
        """
        self._checking = False
        self._running = False


    def __repr__(self):
        return '<beacon.Monitor for %s>' % self._query


    def __del__(self):
        log.info('delete %s', self)
