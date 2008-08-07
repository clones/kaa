# -*- coding: iso-8859-1 -*-
# -----------------------------------------------------------------------------
# $Id$
# -----------------------------------------------------------------------------
# kaa.canvas - Canvas library based on kaa.evas
# Copyright (C) 2005, 2006 Jason Tackaberry
#
# First Edition: Dirk Meyer <dischi@freevo.org>
# Maintainer:    Dirk Meyer <dischi@freevo.org>
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

__all__ = [ 'DirectFBCanvas' ]

from kaa.canvas import Canvas
from kaa.display.dfb import EvasDirectFB

class DirectFBCanvas(Canvas):

    def __init__(self, size):
        self._dfb = EvasDirectFB(size)
        super(DirectFBCanvas, self).__init__()

        self["size"] = size

        self._wrap(self._dfb.get_evas())

    def _render(self):
        regions = self._o.render()
        if regions:
            self.signals["updated"].emit(regions)
        return regions
