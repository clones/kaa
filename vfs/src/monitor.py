# -*- coding: iso-8859-1 -*-
# -----------------------------------------------------------------------------
# monitor.py - Monitor for changes in the VFS
# -----------------------------------------------------------------------------
# $Id: device.py 799 2005-09-16 14:27:36Z rshortt $
#
# TODO: handle all the FIXME and TODO comments inside this file and
#       add docs for functions, variables and how to use this file
#
# -----------------------------------------------------------------------------
# kaa-vfs - A virtual filesystem with metadata
# Copyright (C) 2005 Dirk Meyer
#
# First Edition: Dirk Meyer <dmeyer@tzi.de>
# Maintainer:    Dirk Meyer <dmeyer@tzi.de>
#
# Please see the file doc/CREDITS for a complete list of authors.
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

from kaa.base.weakref import weakref
from kaa.notifier import OneShotTimer, WeakTimer

import parser
import util

class Notification(object):
    def __init__(self, remote, id):
        self.remote = remote
        self.id = id

    def __call__(self, *args, **kwargs):
        self.remote(self.id, __ipc_oneway=True, *args, **kwargs)


class Monitor(object):
    """
    Monitor query for changes and call callback.
    """
    NEXT_ID = 1
    def __init__(self, callback, db, query):
        self.id = Monitor.NEXT_ID
        Monitor.NEXT_ID += 1
        self.callback = Notification(callback, self.id)

        self._db = db
        self._query = query
        self._checker = None
        if self._query.has_key('dirname'):
            # FIXME: use inotify for monitoring, this will also fix the
            # problem when files grow because they are copied right
            # now and the first time we had no real information
            WeakTimer(self.check, self._query['dirname']).start(1)


    def check(self, dirname):
        if self._checker:
            # still checking
            return True
        current = util.listdir(dirname, self._db.dbdir, url=True, sort=True)
        if len(current) != len(self.items):
            OneShotTimer(self.update, True).start(0)
            return True
        for pos, url in enumerate(current):
            if self.items[pos].url != url:
                OneShotTimer(self.update, True).start(0)
                return True
        return True


    def update(self, send_changed=False):
        if not self._query.has_key('dirname'):
            # no idea how to monitor this right now
            self.callback('up-to-date')
            return
        to_check = []
        query = self._db.query(**self._query)
        self.items = query.get()
        for item in self.items:
            mtime = parser.get_mtime(item)
            if not mtime:
                continue
            if item.data['mtime'] == mtime:
                continue
            to_check.append(weakref(item))
        if to_check:
            self._checker = weakref(parser.Checker(self._db, to_check, self.callback))
        elif send_changed:
            self.callback('changed')
            self.callback('up-to-date')
        else:
            self.callback('up-to-date')

    def __str__(self):
        return '<vfs.Monitor for %s>' % self._query


    def __del__(self):
        print 'del', self
