# -*- coding: iso-8859-1 -*-
# -----------------------------------------------------------------------------
# channel.py - channel class
# -----------------------------------------------------------------------------
# $Id$
# -----------------------------------------------------------------------------
# kaa.epg - EPG Database
# Copyright (C) 2004-2007 Jason Tackaberry, Dirk Meyer, Rob Shortt
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

class Channel(object):
    """
    kaa.epg.Channel class.
    """
    def __init__(self, dbdata):
        self._dbdata = dbdata

    def __getattr__(self, attr):
        """
        Defer accessing the ObjectRow (dbdata) until referenced, as this will
        defer any ObjectRow unpickling.
        """
        if attr != '_dbdata' and hasattr(self, '_dbdata'):
            self.db_id = self._dbdata['id']
            self.tuner_id  = self._dbdata['tuner_id']
            self.name = self._dbdata['name']
            self.long_name = self._dbdata['long_name']
            del self._dbdata
        return self.__getattribute__(attr)

    def __repr__(self):
        return '<kaa.epg.Channel %s>' % self.name
