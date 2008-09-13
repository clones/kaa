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

from kaa import unicode_to_str

class Program(object):
    """
    kaa.epg.Program class.
    """
    def __init__(self, channel, dbdata):
        self.channel = channel
        self._dbdata = dbdata

    def __getattr__(self, attr):
        """
        Defer accessing the ObjectRow (dbdata) until referenced, as this will
        defer any ObjectRow unpickling.
        """
        if attr != '_dbdata':
            self.start = self._dbdata.get('start', 0)
            self.stop = self._dbdata.get('stop', 0)
            self.title = self._dbdata.get('title', u'')
            self.description = self._dbdata.get('desc', u'')
            self.subtitle = self._dbdata.get('subtitle',  u'')
            self.episode = self._dbdata.get('episode')
            self.genres = self._dbdata.get('genres', [])
            self.advisories = self._dbdata.get('advisories', [])
            self.rating = self._dbdata.get('rating')
            self.score = self._dbdata.get('score')
            del self._dbdata
        return self.__getattribute__(attr)

    def __repr__(self):
        return '<kaa.epg.Program %s>' % unicode_to_str(self.title)
