# -*- coding: iso-8859-1 -*-
# -----------------------------------------------------------------------------
# monitor.py - Monitor for changes in Beacon
# -----------------------------------------------------------------------------
# $Id$
#
# -----------------------------------------------------------------------------
# kaa-beacon - A virtual filesystem with metadata
# Copyright (C) 2006 Dirk Meyer
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
import parser
from item import Item

# get logging object
log = logging.getLogger('beacon.monitor')

class Notification(object):
    def __init__(self, client, id):
        self.rpc = client.rpc
        self.id = id

    def __call__(self, *args, **kwargs):
        try:
            self.rpc('notify', self.id, *args, **kwargs)
        except IOError:
            pass

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

_master = None

class Monitor(object):
    """
    Monitor query for changes and call the client.
    """
    def __init__(self, client, db, server, id, query):
        global _master
        log.info('create new monitor %s' % id)
        self.id = id
        self.notify_client = Notification(client, self.id)
        self._server = server
        self._db = db
        self._query = query
        self._checking = False
        self._running = True
        self._check_changes = []
        self.items = self._db.query(**self._query)
        if not _master:
            _master = Master(db)
        _master.connect(self)
        if self.items and isinstance(self.items[0], Item):
            self._initial_scan(True)

        # FIXME: how to get updates on directories not monitored by
        # inotify? Maybe poll the dirs when we have a query with
        # dirname it it?
        

    def check(self, changes):
        """
        This function compares the last query result with the current db status
        and will inform the client when there is a change.
        """
        if not self._running:
            return True
        
        if self._checking:
            # Still checking. Question: What happens if new files are added during
            # scan? For one part, the changes here here the item changes
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
            self.items = current
            self.notify_client('changed')
            return True

        # Same length and length is 0. No change here
        if len(current) == 0:
            return True

        # Same length, check for changes inside the items
        if isinstance(current[0], Item):
            for i in current:
                # We only compare the ids. If an item had no id before and
                # has now we can't detect it. But we only call this function
                # if we have a full scanned db. So an empty id also triggers
                # the update call.
                if i._beacon_id in changes or not i._beacon_id:
                    self.items = current
                    self.notify_client('changed')
                    return True
            return True

        # Same length and items are not type Item. This means they are strings
        # from 'attr' query.
        last = self.items[:]
        for c in current:
            if last.pop(0) != c:
                self.items = current
                self.notify_client('changed')
                return True
        return True


    @yield_execution(0.01)
    def _initial_scan(self, first_call):
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

        if not changed and first_call:
            # no changes but it was our first call. Tell the client that
            # everything is checked
            self.notify_client('checked')
            self._checking = False
            yield False

        if not changed:
            # no changes but send the 'changed' ipc to the client
            self.notify_client('changed')
            self._checking = False
            yield False

        if not first_call and len(changed) > 10:
            # do not wait to send the changed signal, it may take a while.
            self.notify_client('changed')

        updated = []
        for pos, item in enumerate(changed):
            self.notify_client('progress', pos+1, len(changed), item.url)
            parser.parse(self._db, item)
            if item._beacon_id:
                self.notify_client('updated', [ (item.url, item._beacon_data) ])
            else:
                updated.append(item)
            yield YieldContinue
            if not self._checking:
                break
            
        self._db.commit()
        self.stop()

        if updated:
            updated = [ (x.url, x._beacon_data) for x in updated ]
            updated.sort(lambda x,y: cmp(x[0], y[0]))
            self.notify_client('updated', updated)

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
        if first_call:
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
