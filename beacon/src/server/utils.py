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

__all__ = [ 'BurstHandler' ]

# kaa imports
import kaa.notifier

class BurstHandler(dict):

    def __init__(self, interval, callback):
        self._ts = {}
        self._timer = kaa.notifier.WeakTimer(self._poll)
        self._timer.start(interval)
        self._callback = callback


    def stop(self):
        self._timer.stop()
        self._ts = {}


    def remove(self, name):
        if not name in self._ts:
            return
        del self._ts[name]


    def active(self, name):
        if not name in self._ts:
            self._ts[name] = False
            return False
        self._ts[name] = True
        return True


    def _poll(self):
        ts = self._ts
        self._ts = {}
        for name in [ name for name, needed in ts.items() if needed ]:
            self._callback(name)
