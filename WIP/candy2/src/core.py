# -*- coding: iso-8859-1 -*-
# -----------------------------------------------------------------------------
# core.py - Basic Classes
# -----------------------------------------------------------------------------
# $Id$
#
# -----------------------------------------------------------------------------
# kaa-candy - Third generation Canvas System using Clutter as backend
# Copyright (C) 2008 Dirk Meyer, Jason Tackaberry
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

__all__ = [ 'Color', 'Font' ]

class Color(list):
    """
    Color object.
    """
    def __init__(self, *col):
        if len(col) > 1:
            return super(Color, self).__init__(col)
        # Convert a 32-bit (A)RGB color
        if col == None:
            return super(Color, self).__init__((0,0,0,255))
        if hasattr(col[0], 'red'):
            # clutter.Color object
            return super(Color, self).__init__((
                col[0].red, col[0].green, col[0].blue, col[0].alpha))
        # convert 0x???????? string
        col = long(col[0], 16)
        a = 255 - ((col >> 24) & 0xff)
        r = (col >> 16) & 0xff
        g = (col >> 8) & 0xff
        b = (col >> 0) & 0xff
        super(Color, self).__init__((r,g,b,a))

    def to_cairo(self):
        """
        Convert to list used by cairo (float values from 0-1)
        """
        return [ x / 255.0 for x in self ]

class Font(object):
    """
    Font object
    """
    def __init__(self, name):
        self.name, size = name.split(':')
        self.size = int(size)
        
