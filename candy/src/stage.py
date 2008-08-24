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

__all__ = [ 'Stage' ]

# python imports
import threading
import time
import logging
import gobject

# kaa imports
import kaa

# kaa.candy imports
from core import is_template
from widgets import Group

import backend
import animation
import candyxml
import config

# get logging object
log = logging.getLogger('kaa.candy')

class Stage(Group):
    """
    kaa.candy window

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
        super(Stage, self).__init__(None, (width, height))
        self.signals = kaa.Signals('key-press', 'resize')
        kaa.signals['step'].connect(self.sync)
        animation.signals['candy-update'].connect(self._candy_sync)

    def candyxml(self, data):
        """
        Load a candyxml file based on the given screen resolution.

        @param data: filename of the XML file to parse or XML data
        @returns: root element attributes and dict of parsed elements
        """
        return candyxml.parse(data, (self.width, self.height))

    def sync(self):
        """
        Called from the mainloop to update all widgets in the clutter thread.
        """
        if not (self._sync_rendering or self._sync_layout or self._sync_properties):
            # No update needed, no need to jump into the clutter thread
            # and return without doing anything usefull.
            return
        if animation.thread_locked():
            animation.thread_leave(force=True)
        event = threading.Event()
        gobject.idle_add(self._candy_sync, event)
        event.wait()

    def _candy_handle_key(self, stage, event):
        """
        Translate clutter keycode to name and emit signal in main loop. This
        function is a callback from clutter.
        """
        key = self._keysyms.get(event.keyval)
        if key is not None:
            kaa.MainThreadCallback(self.signals['key-press'].emit)(key)

    def _candy_sync(self, event=None):
        """
        Execute update inside safe try/except environment
        """
        try:
            if config.performance_debug:
                t1 = time.time()
            if self._sync_rendering:
                self._candy_prepare_render()
                self._sync_rendering = False
                self._candy_render()
            if self._sync_layout:
                self._sync_layout = False
                self._candy_sync_layout()
            if self._sync_properties:
                self._candy_sync_properties()
                self._sync_properties = {}
            if config.performance_debug:
                diff = time.time() - t1
                if diff > 0.05:
                    log.warning('candy_sync() took %2.3f secs' % diff)
        except Exception, e:
            log.exception('kaa.candy.sync')
        if event:
            event.set()
        return False

    def _candy_render(self):
        """
        Render the widget. This will only be called on stage creation
        """
        if not self._obj:
            self._obj = backend.Stage()
            self._obj.set_size(self.width, self.height)
            self._obj.connect('key-press-event', self._candy_handle_key)
            self._obj.set_color(backend.Color(0, 0, 0, 0xff))
            self._keysyms = {}
            # get list of clutter key code. We must access the module
            # first before it is working, therefor we access Left.
            backend.keysyms.Left
            for name in dir(backend.keysyms):
                if len(name) == 2 and name.startswith('_'):
                    self._keysyms[getattr(backend.keysyms, name)] = name[1]
                if not name.startswith('_'):
                    self._keysyms[getattr(backend.keysyms, name)] = name
            self._obj.show()
        if 'size' in self._sync_properties:
            # object already created but user changed the size
            self._obj.set_size(self.width, self.height)
            self.signals['resize'].emit()
        super(Stage, self)._candy_render()
