# -*- coding: iso-8859-1 -*-
# -----------------------------------------------------------------------------
# channel.py - channel class
# -----------------------------------------------------------------------------
# $Id$
# -----------------------------------------------------------------------------
# kaa.epg - EPG Database
# Copyright (C) 2004-2005 Jason Tackaberry, Dirk Meyer, Rob Shortt
#
# First Edition: Jason Tackaberry <tack@sault.org>
# Maintainer:    Dirk Meyer <dischi@freevo.org>
#                Rob Shortt <rob@tvcentric.com>
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
## You should have received a copy of the GNU General Public License along
# with this program; if not, write to the Free Software Foundation, Inc.,
# 59 Temple Place, Suite 330, Boston, MA 02111-1307 USA
#
# -----------------------------------------------------------------------------

# python imports
from kaa.weakref import weakref
import time


class Channel(object):
    """
    kaa.epg channel class.
    """
    def __init__(self, tuner_id, name, long_name, epg):
        self.db_id      = None
        self.tuner_id   = tuner_id
        self.name       = name
        self.long_name  = long_name
        self._epg       = weakref(epg)

        # kludge - remove
        self.id = name


    def get_programs(self, t = None, callback = None):
        """
        Get programs from a specific time.
        """
        if not t:
            t = time.time()

        if self._epg:
            return self._epg.search(time = t, channel = self, callback = callback)
        else:
            return []
