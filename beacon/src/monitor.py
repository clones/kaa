# -*- coding: iso-8859-1 -*-
# -----------------------------------------------------------------------------
# monitor.py - Monitor for changes in Beacon
# -----------------------------------------------------------------------------
# $Id$
#
# TODO: handle all the FIXME and TODO comments inside this file and
#       add docs for functions, variables and how to use this file
#
# -----------------------------------------------------------------------------
# kaa-beacon - A virtual filesystem with metadata
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
from kaa.weakref import weakref
from kaa.notifier import WeakTimer, Timer, execute_in_timer, Callback

# kaa.beacon imports
import parser
import cdrom
from item import Item

# get logging object
log = logging.getLogger('beacon')

class Notification(object):
    def __init__(self, remote, id):
        self.remote = remote
        self.id = id

    def __call__(self, *args, **kwargs):
        self.remote(self.id, __ipc_oneway=True, __ipc_noproxy_args=True, *args, **kwargs)


class Monitor(object):
    """
    Monitor query for changes and call callback.
    """

    def __init__(self, callback, db, server, id, query):
        log.debug('create new monitor %s' % id)
        self.id = id
        self.callback = Notification(callback, self.id)
        self._server = server
        self._db = db
        self._query = query
        self._checker = None
        self.items = self._db.query(**self._query)
        if self.items and isinstance(self.items[0], Item):
            self._scan(True)
        self._poll()

#         if self._query.has_key('dirname') and \
#            (not self._query.has_key('recursive') or not self._query['recursive']):
#             # TODO: use inotify for monitoring, this will also fix the
#             # problem when files grow because they are copied right
#             # now and the first time we had no real information
#             dirname = self._query['dirname']
#             for m in self._db._mountpoints:
#                 if dirname.startswith(m.directory):
#                     break
#             WeakTimer(self.check, dirname, m).start(1)
#         if self._query.has_key('device'):
#             # monitor a media
#             # TODO: support other stuff except cdrom
#             # FIXME: support removing the monitor :)
#             cdrom.monitor(query['device'], weakref(self), db, self._server)
            

    @execute_in_timer(WeakTimer, 1)
    def _poll(self):
        if self._checker:
            # still checking
            return True
        current = self._db.query(**self._query)
        if len(current) != len(self.items):
            self.items = current
            if (current and isinstance(current[0], Item)) or \
               (self.items and isinstance(self.items[0], Item)):
                self._scan(False)
            else:
                self.callback('changed')
            return True
        if len(current) == 0:
            return True
        if isinstance(current[0], Item):
            for pos, c in enumerate(current):
                if self.items[pos].url != c.url:
                    self.items = current
                    self._scan(False)
                    return True
        else:
            for pos, c in enumerate(current):
                if self.items[pos] != c:
                    self.items = current
                    self.callback('changed')
                    return True
        return True


    def _scan(self, first_call):
        self._scan_step(self.items[:], [], first_call)

        
    @execute_in_timer(Timer, 0.001, type='once')
    def _scan_step(self, items, changed, first_call):
        """
        Find changed items in 'items' and add them to changed.
        """
        if not items:
            self._update(changed, first_call)
            return False
        c = 0
        while items:
            c += 1
            if c > 20:
                return True
            i = items.pop(0)
            # FIXME: check parents
            if i._beacon_changed():
                changed.append(i)
        return True


    def _update(self, changed, first_call):
        if changed:
            cb = Callback(self.checked, first_call)
            c = parser.Checker(self.callback, self._db, changed, cb)
            self._checker = c
            if not first_call and len(changed) > 10:
                self.callback('changed')
        elif first_call:
            self.callback('checked')
        else:
            self.callback('changed')


    def checked(self, first_call):
        self._checker = None
        self.callback('changed')
        if first_call:
            self.callback('checked')

        
    def stop(self):
        if self._checker:
            self._checker.stop()
        self._checker = None

        
    #     if self._query.has_key('device'):
#             log.info('unable to update device query, just send notification here')
#             # device query, can't update it
#             if send_checked:
#                 log.info('client.checked')
#                 self.callback('checked')
#                 return

#         last_parent = None
#         t1 = time.time()
#         for i in self.items:
#             # FIXME: this does not scale very good. For many items like a
#             # recursive dir search it can take several seconds to scan all mtimes
#             # and this is not an option.
#             if not isinstance(i, item.Item):
#                 # TODO: don't know how to monitor other types
#                 continue

#             # check parent and parent.parent mtime. Notice. The root
#             # dir has also a parent, the media itself. So we need to stop at
#             # parent.parent == None.
#             parent = i.parent
#             parent_check = []
#             while last_parent != parent and parent and parent.parent:
#                 mtime = parser.get_mtime(parent)
#                 if mtime and parent.data['mtime'] != mtime and not parent in to_check:
#                     parent_check.append(weakref(parent))
#                 parent = parent.parent
#             if parent_check:
#                 parent_check.reverse()
#                 to_check += parent_check
#             last_parent = i.parent
            
#             mtime = parser.get_mtime(i)
#             if not mtime:
#                 continue
#             if i.data['mtime'] == mtime:
#                 continue
#             to_check.append(weakref(i))

#         if to_check:
#             # FIXME: a constantly growing file like a recording will result in
#             # a huge db activity on both client and server because checker calls
#             # update again and the mtime changed.
#             self._checker = weakref(parser.Checker(weakref(self), self._db, to_check))
#         elif send_checked:
#             log.info('client.checked')
#             self.callback('checked')


    def __repr__(self):
        return '<beacon.Monitor for %s>' % self._query


    def __del__(self):
        log.debug('del %s' % repr(self))
