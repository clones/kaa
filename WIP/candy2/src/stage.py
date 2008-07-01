# -*- coding: iso-8859-1 -*-
# -----------------------------------------------------------------------------
# stage.py - Clutter Stage Wrapper
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

"""
kaa.candy window for widgets
"""

__all__ = [ 'Stage' ]

# clutter imports
import clutter

# kaa imports
import kaa

# kaa.candy imports
from core import threaded, is_template

class Stage(object):
    """
    Wrapper around clutter.Stage.
    @ivar signals: kaa.Signal dictionary for the object
      - key-press: sends a key pressed in the window. The signal is emited in
           the kaa mainloop.
    """
    def __init__(self, (width, height)):
        """
        Create a window with the given geometry
        @param width: width of the window
        @param height: height of the window
        """
        self.signals = kaa.Signals('key-press')
        self._geomertry = width, height
        self._stage = clutter.Stage()
        self._stage.set_size(width, height)
        self._stage.connect('key-press-event', self._handle_key)
        self._stage.set_color(clutter.Color(0, 0, 0, 0xff))
        self._keysyms = {}
        # get list of clutter key code. We must access the module
        # first before it is working, therefor we access Left.
        clutter.keysyms.Left
        for name in dir(clutter.keysyms):
            if not name.startswith('_'):
                self._keysyms[getattr(clutter.keysyms, name)] = name
        self._stage.show()

    def _handle_key(self, stage, event):
        """
        Translate clutter keycode to name and emit signal in main loop. This
        function is a callback from clutter.
        """
        key = self._keysyms.get(event.keyval)
        if key is not None:
            kaa.MainThreadCallback(self.signals['key-press'].emit)(key)

    @threaded()
    def add(self, child, visible=True):
        """
        Add the child to the screen.
        @param child: Widget or widget Template object
        @param visible: set the child status to visible when adding
        """
        if is_template(child):
            child = child()
        if visible:
            child.show()
        self._stage.add(child)

    @threaded()
    def remove(self, child):
        """
        Remove the child from the screen.
        @param child: child connected to the window
        """
        self._stage.remove(child)
