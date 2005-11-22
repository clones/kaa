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


# python imports
import logging

# kaa imports
from kaa.base.weakref import weakref
from kaa.notifier import OneShotTimer, WeakTimer

# kaa.vfs imports
import parser
import util
import item
import cdrom

# get logging object
log = logging.getLogger('vfs')

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
    def __init__(self, callback, db, server, query):
        self.id = Monitor.NEXT_ID
        Monitor.NEXT_ID += 1
        self.callback = Notification(callback, self.id)
        self._server = server
        self._db = db
        self._query = query
        self._checker = None
        if self._query.has_key('dirname'):
            # TODO: use inotify for monitoring, this will also fix the
            # problem when files grow because they are copied right
            # now and the first time we had no real information
            WeakTimer(self.check, self._query['dirname']).start(1)
        if self._query.has_key('device'):
            # monitor a media
            # TODO: support other stuff except cdrom
            # FIXME: support removing the monitor :)
            cdrom.monitor(query['device'], weakref(self), db, self._server)
            
            
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


    def update(self, send_checked=True):
        to_check = []
        import time
        t1 = time.time()
        self.items = self._db.query(**self._query)
        print 'monitor query took', time.time() - t1
        if self._query.has_key('device'):
            log.info('unable to update device query, just send notification here')
            # device query, can't update it
            if send_checked:
                log.info('client.checked')
                self.callback('checked')
                return

        # TODO: we should also check the parent and the parent of the parent,
        # maybe a cover was added somewhere in the path.
        t1 = time.time()
        for i in self.items:
            if not isinstance(i, item.Item):
                # TODO: don't know how to monitor other types
                continue
            mtime = parser.get_mtime(i)
            if not mtime:
                continue
            if i.data['mtime'] == mtime:
                continue
            to_check.append(weakref(i))
        print 'mtime query took', time.time() - t1
        if to_check:
            # FIXME: a constantly growing file like a recording will result in
            # a huge db activity on both client and server because checker calls
            # update again and the mtime changed.
            self._checker = weakref(parser.Checker(weakref(self), self._db, to_check))
        elif send_checked:
            log.info('client.checked')
            self.callback('checked')


    def __str__(self):
        return '<vfs.Monitor for %s>' % self._query


    def __del__(self):
        log.debug('del %s' % self)
