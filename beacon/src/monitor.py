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
from kaa.notifier import WeakTimer, WeakOneShotTimer, Timer, execute_in_timer, Callback

# kaa.beacon imports
import parser
import cdrom
from item import Item

# get logging object
log = logging.getLogger('beacon.monitor')

class Notification(object):
    def __init__(self, remote, id):
        self.remote = remote
        self.id = id

    def __call__(self, *args, **kwargs):
        self.remote(self.id, __ipc_oneway=True, __ipc_noproxy_args=True, *args, **kwargs)


class Master(object):
    def __init__(self, db):
        self.monitors = []
        self.timer = Timer(self.check)
        db.signals['changed'].connect(self.changed)
        
    def connect(self, monitor):
        self.monitors.append((weakref(monitor), []))
        
    def changed(self, changes):
        for m, c in self.monitors:
            c.extend(changes)
        if not self.timer.active():
            self.timer.start(0.02)

    def check(self):
        if not self.monitors:
            return False
        monitor, changes = self.monitors.pop(0)
        if monitor == None:
            return True
        if changes:
            monitor.check(changes)
        self.monitors.append((monitor, []))

_master = None

class Monitor(object):
    """
    Monitor query for changes and call callback.
    """
    def __init__(self, callback, db, server, id, query):
        global _master
        log.debug('create new monitor %s' % id)
        self.id = id
        self.callback = Notification(callback, self.id)
        self._server = server
        self._db = db
        self._query = query
        self._checker = None
        self._check_changes = []
        self.items = self._db.query(**self._query)
        if not _master:
            _master = Master(db)
        _master.connect(self)
        if self.items and isinstance(self.items[0], Item):
            self._scan(True)

        # FIXME: how to get updates on directories not monitored by
        # inotify? Maybe poll the dirs when we have a query with
        # dirname it it?
        

    def check(self, changes):
        """
        This function compares the last query result with the current db status
        and will inform the client when there is a change.
        """
        if self._checker:
            # Still checking. FIXME: what happens if new files are added during
            # scan? For one part, the changes here here the item changes itself,
            # so we would update the client all the time. So it is better to wait
            # here. Note: with inotify support this should not happen often.
            self._check_changes.extend(changes)
            return True

        if self._check_changes:
            changes = self._check_changes + changes
            self._check_changes = []
            
        current = self._db.query(**self._query)

        # The query result length is different, this is a change
        if len(current) != len(self.items):
            self.items = current
            self.callback('changed')
            return True

        # Same length and length is 0. No change here
        if len(current) == 0:
            return True

        # Same length, check for changes inside the items
        if isinstance(current[0], Item):
            for i in current:
                if i._beacon_id in changes:
                    self.items = current
                    self.callback('changed')
                    return True
            return True

        # Same length, check if the strings itself did not change
        for pos, c in enumerate(current):
            if self.items[pos] != c:
                self.items = current
                self.callback('changed')
                return True
        return True


    def _scan(self, first_call):
        """
        Start scanning the current list of items if they need to be updated.
        With a full structure covered by inotify, there should be not changes.
        """
        self._scan_step(self.items[:], [], first_call)

        
    @execute_in_timer(Timer, 0.001, type='once')
    def _scan_step(self, items, changed, first_call):
        """
        Find changed items in 'items' and add them to changed.
        """
        if not items:
            if not changed and first_call:
                # no changes but it was our first call. Tell the client that everything
                # is checked
                self.callback('checked')
                return False
            if not changed:
                # no changes but send the 'changed' ipc to the client
                self.callback('changed')
                return False
            # We have some items that need an update. This will create a parser
            # object checking all items in the list.
            cb = Callback(self.checked, first_call)
            c = parser.Checker(self.callback, self._db, changed, cb)
            self._checker = c
            if not first_call and len(changed) > 10:
                # do not wait for the parser to send the changed signal, it may
                # take a while.
                self.callback('changed')
            return False

        c = 0
        while items:
            c += 1
            if c > 20:
                # stop it and continue in the next step
                return True
            i = items.pop(0)
            # FIXME: check parents
            if i._beacon_changed():
                changed.append(i)
        return True


    def checked(self, first_call):
        self._checker = None
        # The client will update its query on this signal, so it should
        # be safe to do the same here. *cross*fingers*
        self.items = self._db.query(**self._query)
        # Do not send 'changed' signal here. The db was changed and the
        # master notification will do the rest. Just to make sure it will
        # happen, start a Timer
        if self._check_changes:
            # Set new check timer. This should not be needed, but just in case :)
            WeakOneShotTimer(self.check, []).start(0.5)
        if first_call:
            self.callback('checked')

        
    def stop(self):
        if self._checker:
            self._checker.stop()
        self._checker = None


    def __repr__(self):
        return '<beacon.Monitor for %s>' % self._query


    def __del__(self):
        log.debug('del %s' % repr(self))
