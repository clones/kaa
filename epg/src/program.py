# -*- coding: iso-8859-1 -*-
# -----------------------------------------------------------------------------
# program.py - program class
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

__all__ = [ 'Program' ]

class Program(object):
    """
    kaa.epg program class.
    """
    def __init__(self, channel, dbdata):
        self.channel = channel
        self._dbdata = dbdata

        self.start = dbdata.get('start', 0)
        self.stop = dbdata.get('stop', 0)
        self.title = dbdata.get('title', u'')
        self.description = dbdata.get('desc', u'')
        self.subtitle = dbdata.get('subtitle',  u'')
        self.episode = dbdata.get('episode', u'')
        self.genre = dbdata.get('genre', u'')

    def __repr__(self):
        return '<kaa.epg.Program %s>' % self.title
