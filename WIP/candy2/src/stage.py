# -*- coding: iso-8859-1 -*-
# -----------------------------------------------------------------------------
# stage.py - Clutter Stage (thread safe)
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

# clutter imports
import clutter

# kaa imports
import kaa

# kaa.candy imports
from core import threaded

class Stage(object):
    """
    Window main window.
    """
    def __init__(self, (width, height)):
        self.signals = kaa.Signals('key-press')
        self._geomertry = width, height
        self._stage = clutter.Stage()
        self._stage.set_size(width, height)
        self._stage.connect('key-press-event', self.handle_key)
        self._stage.set_color(clutter.Color(0, 0, 0, 0xff))
        self._keysyms = {}
        # get list of clutter key code. We must access the module
        # first before it is working, therefor we access Left.
        clutter.keysyms.Left
        for name in dir(clutter.keysyms):
            if not name.startswith('_'):
                self._keysyms[getattr(clutter.keysyms, name)] = name
        self._stage.show()

    def handle_key(self, stage, event):
        """
        Translate clutter keycode to name and emit signal in main loop.
        """
        key = self._keysyms.get(event.keyval)
        if key is not None:
            kaa.MainThreadCallback(self.signals['key-press'].emit)(key)

    @threaded()
    def add(self, child, visible=True):
        """
        Add the child to the screen.
        """
        if visible:
            child.show()
        self._stage.add(child)

    @threaded()
    def remove(self, child):
        """
        Remove the child from the screen.
        """
        self._stage.remove(child)
