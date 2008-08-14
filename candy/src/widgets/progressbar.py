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

# kaa imports
from kaa.utils import property

# kaa.candy imports
from ..core import is_template
from container import Group

class Progressbar(Group):
    """
    Widget showing a progressbar. Only the bar is drawn, the border has
    to be created ouside this widget.
    """
    candyxml_name = 'progressbar'

    __max = 0
    __progress = 0

    def __init__(self, pos, size, progress):
        super(Progressbar, self).__init__(pos, size)
        if is_template(progress):
            progress = progress()
        self._bar = progress
        self._bar.x = 0
        self._bar.y = 0
        self._bar.height = self.height
        self._bar.parent = self

    @property
    def max(self):
        return self.__max

    @max.setter
    def max(self, value):
        self.__max = value

    @property
    def progress(self):
        return self.__progress

    @progress.setter
    def progress(self, value):
        """
        Set a new progress and redraw the widget.
        """
        self.__progress = value
        self._queue_sync(rendering=True)

    def inc(self):
        """
        Increase progress by one
        """
        self.__progress += 1
        self._queue_sync(rendering=True)
        
    def _candy_render(self):
        """
        Render the widget
        """
        if 'size' in self._sync_properties:
            self._bar.height = self.height
        super(Progressbar, self)._candy_render()
        pos = float(self.__progress) / max(self.__max, self.__progress, 0.1)
        self._bar.width = int(max(pos * self.width, 1))

    @classmethod
    def candyxml_parse(cls, element):
        """
        Parse the XML element for parameter to create the widget.
        """
        return super(Progressbar, cls).candyxml_parse(element).update(
            progress=element[0].xmlcreate())


# register widget to candyxml
Progressbar.candyxml_register()
