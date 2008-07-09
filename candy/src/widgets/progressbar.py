# -*- coding: iso-8859-1 -*-
# -----------------------------------------------------------------------------
# progressbar.py - Progressbar Widget
# -----------------------------------------------------------------------------
# $Id$
#
# -----------------------------------------------------------------------------
# kaa-candy - Third generation Canvas System using Clutter as backend
# Copyright (C) 2008 Dirk Meyer, Jason Tackaberry
#
# First Version: Dirk Meyer <dischi@freevo.org>
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

# kaa.candy imports
from ..core import is_template, threaded
import core

class Progressbar(core.Group):
    """
    Widget showing a progressbar. Only the bar is drawn, the border has
    to be created ouside this widget.
    """
    candyxml_name = 'progressbar'

    def __init__(self, pos, size, progress):
        super(Progressbar, self).__init__(pos, size)
        self._width = size[0]
        self._max = 0
        if is_template(progress):
            progress = progress(pos=(0,0), size=size)
            # FIXME: set pos and size for non templates
        self._progress = progress
        self._progress.set_width(1)
        self._progress.show()
        self.add(self._progress)

    @threaded()
    def set_max(self, max):
        """
        Set maximum value of the progress.
        """
        self._max = max

    @threaded()
    def set_progress(self, value):
        """
        Set a new progress and redraw the widget.
        """
        pos = float(value) / max(self._max, value, 0.1)
        self._progress.set_width(int(max(pos * self._width, 1)))

    @classmethod
    def candyxml_parse(cls, element):
        """
        Parse the XML element for parameter to create the widget.
        """
        return super(Progressbar, cls).candyxml_parse(element).update(
            progress=element[0].xmlcreate())


# register widget to candyxml
Progressbar.candyxml_register()
