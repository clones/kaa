# -*- coding: iso-8859-1 -*-
# -----------------------------------------------------------------------------
# utils.py - Some utils for the server
# -----------------------------------------------------------------------------
# $Id$
#
# -----------------------------------------------------------------------------
# kaa.beacon.server - A virtual filesystem with metadata
# Copyright (C) 2007 Dirk Meyer
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

__all__ = [ 'BurstHandler', 'do_thumbnail' ]

# kaa imports
import kaa.notifier

class BurstHandler(object):
    """
    Monitor growing files.
    """

    _all_instances = []

    def __init__(self, interval, callback):
        self._ts = {}
        self._thumb = {}
        self._timer = kaa.notifier.WeakTimer(self._poll)
        self._timer.start(interval)
        self._callback = callback
        self._all_instances.append(self)


    def remove(self, name):
        """
        Remove a file from the list of growing files.
        """
        if name in self._ts:
            del self._ts[name]
        if name in self._thumb:
            del self._thumb[name]


    def is_growing(self, name):
        """
        Return True if the file is growing. Detection is based on the
        frequency this function is called.
        """
        if not name in self._ts:
            self._ts[name] = False
            return False
        self._ts[name] = True
        return True


    def _do_thumbnail(self, name):
        """
        Check if a thumbnail should be created.
        """
        if not name in self._ts:
            # not in the list of growing files
            return True
        if not name in self._thumb:
            self._thumb[name] = 0
            # first time is always ok
            return True
        self._thumb[name] += 1
        return (self._thumb[name] % 10) == 0


    def _poll(self):
        """
        Run callback on all growing files.
        """
        ts = self._ts
        self._ts = {}
        for name in [ name for name, needed in ts.items() if needed ]:
            self._callback(name)


def do_thumbnail(name):
    """
    Global function to check if a thumbnail should be created.
    """
    for i in BurstHandler._all_instances:
        if i._do_thumbnail(name):
            return True
    return False
