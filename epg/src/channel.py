# -*- coding: iso-8859-1 -*-
# -----------------------------------------------------------------------------
# channel.py - channel class
# -----------------------------------------------------------------------------
# $Id$
# -----------------------------------------------------------------------------
# kaa.epg - EPG Database
# Copyright (C) 2004-2006 Jason Tackaberry, Dirk Meyer, Rob Shortt
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

__all__ = [ 'Channel' ]

# python imports
import time

# kaa imports
from kaa.weakref import weakref

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


    def __repr__(self):
        return '<kaa.epg.Channel %s>' % self.name
