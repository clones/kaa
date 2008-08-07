# -*- coding: iso-8859-1 -*-
# -----------------------------------------------------------------------------
# $Id$
# -----------------------------------------------------------------------------
# kaa.canvas - Canvas library based on kaa.evas
# Copyright (C) 2005, 2006 Jason Tackaberry
#
# First Edition: Jason Tackaberry <tack@sault.org>
# Maintainer:    Jason Tackaberry <tack@sault.org>
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

__all__ = [ 'BufferCanvas' ]


from kaa.canvas import Canvas
from kaa import evas


class BufferCanvas(Canvas):
    def __init__(self, size = None, buffer = None):
        super(BufferCanvas, self).__init__()
        if size != None:
            self["size"] = size
            self.create(size, buffer)

    def create(self, size, buffer = None):
        canvas = evas.EvasBuffer(size, depth = evas.ENGINE_BUFFER_DEPTH_ARGB32, buffer = buffer)
        if self["size"] == ("100%", "100%"):
            self["size"] = size
        self._wrap(canvas)
        self._canvased(self)

    def get_buffer(self):
        if not self._o:
            return None
        return self._o.buffer_get()

    def _render(self):
        regions = super(BufferCanvas, self)._render()
        stride = self['size'][0] * 4
        buf = self.get_buffer()
        for x, y, w, h in regions:
            for i in range(y, y+h):
                evas.data_argb_unpremul(buf, i*stride+(x*4), w*4)
        return regions

