# -*- coding: iso-8859-1 -*-
# -----------------------------------------------------------------------------
# program.py - program class
# -----------------------------------------------------------------------------
# $Id$
# -----------------------------------------------------------------------------
# kaa.epg - EPG Database
# Copyright (C) 2004-2008 Jason Tackaberry, Dirk Meyer, Rob Shortt
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

__all__ = [ 'Program' ]

from datetime import datetime

from kaa import unicode_to_str
import kaa.dateutils


class Program(object):
    """
    kaa.epg.Program class.
    """
    # Constants for the flags bitmask
    #: If the program is broadcast in HD
    FLAG_HDTV = 1
    #: If the program is a premiere (e.g. new episode of a show).
    FLAG_NEW = 2
    #: If closed captioning is available for the program.
    FLAG_CC = 4

    def __init__(self, channel, dbdata):
        self.channel = channel
        self._dbdata = dbdata


    def __getattr__(self, attr):
        """
        Defer accessing the ObjectRow (dbdata) until referenced, as this will
        defer any ObjectRow unpickling.
        """
        if hasattr(self, '_dbdata') and attr != '_dbdata':
            self.db_id = self._dbdata.get('type'), self._dbdata.get('id')
            # Unix timestamps are always seconds since epoch UTC.
            self.start_timestamp = self._dbdata.get('start', 0)
            self.stop_timestamp = self._dbdata.get('stop', 0)
            # Timezone-aware datetime objects in the local timezone.
            self.start = datetime.fromtimestamp(self.start_timestamp, kaa.dateutils.local)
            self.stop = datetime.fromtimestamp(self.stop_timestamp, kaa.dateutils.local)

            self.title = self._dbdata.get('title', u'')
            self.description = self._dbdata.get('desc', u'')
            self.subtitle = self._dbdata.get('subtitle',  u'')
            self.episode = self._dbdata.get('episode')
            self.genres = self._dbdata.get('genres', [])
            self.advisories = self._dbdata.get('advisories', [])
            self.rating = self._dbdata.get('rating')
            self.score = self._dbdata.get('score')
            self.flags = self._dbdata.get('flags')
            del self._dbdata
        return self.__getattribute__(attr)

    def __repr__(self):
        return '<kaa.epg.Program %s>' % unicode_to_str(self.title)
