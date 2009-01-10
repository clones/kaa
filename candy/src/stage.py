# -*- coding: iso-8859-1 -*-
# -----------------------------------------------------------------------------
# stage.py - Clutter Stage Wrapper
# -----------------------------------------------------------------------------
# $Id$
#
# -----------------------------------------------------------------------------
# kaa-candy - Third generation Canvas System using Clutter as backend
# Copyright (C) 2008-2009 Dirk Meyer, Jason Tackaberry
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
import os
import threading
import time
import fcntl
import logging
import gobject

# kaa imports
import kaa

# kaa.candy imports
from widgets import Group

import backend
import animation
import candyxml
import config

# get logging object
log = logging.getLogger('kaa.candy')

class Stage(Group):

    __wakeup = True
    __clutter_thread = None

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
        animation.signals['candy-update'].connect(self._clutter_sync)
        # We need the render pipe, the 'step' signal is not enough. It
        # is not troggered between timer and select and a change done
        # in a timer may get lost.
        self._render_pipe = os.pipe()
        fcntl.fcntl(self._render_pipe[0], fcntl.F_SETFL, os.O_NONBLOCK)
        fcntl.fcntl(self._render_pipe[1], fcntl.F_SETFL, os.O_NONBLOCK)
        kaa.IOMonitor(self.sync).register(self._render_pipe[0])
        os.write(self._render_pipe[1], '1')

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
        # read the socket to handle the sync
        try:
            os.read(self._render_pipe[0], 1)
        except OSError:
            pass
        if not (self._sync_rendering or self._sync_layout or self._sync_properties):
            # No update needed, no need to jump into the clutter thread
            # and return without doing anything usefull.
            self.__wakeup = False
            return
        if animation.thread_locked():
            animation.thread_leave(force=True)
        event = threading.Event()
        gobject.idle_add(self._clutter_sync, event)
        event.wait()

    def _clutter_handle_key(self, stage, event):
        """
        Translate clutter keycode to name and emit signal in main loop. This
        function is a callback from clutter.
        """
        key = self._keysyms.get(event.keyval)
        if key is not None:
            kaa.MainThreadCallback(self.signals['key-press'].emit)(key)

    def _schedule_sync(self):
        """
        Schedule sync
        """
        if not self.__wakeup:
            # set wakeup flag
            self.__wakeup = True
            if self.__clutter_thread != threading.currentThread():
                # we are in the clutter thread, either because of sync
                # itself or because of animations. In both cases the
                # sync will take care of the rendering without putting
                # something in the pipe.
                os.write(self._render_pipe[1], '1')

    def _queue_rendering(self):
        """
        Queue rendering on the next sync.
        """
        super(Stage, self)._queue_rendering()
        self._schedule_sync()

    def _queue_sync_layout(self):
        """
        Queue re-layout to be called on the next sync.
        """
        super(Stage, self)._queue_sync_layout()
        self._schedule_sync()

    def _queue_sync_properties(self, *properties):
        """
        Queue clutter properties to be set on the next sync.
        """
        super(Stage, self)._queue_sync_properties(*properties)
        self._schedule_sync()

    def _clutter_sync(self, event=None):
        """
        Execute update inside safe try/except environment
        """
        if not self.__clutter_thread:
            self.__clutter_thread = threading.currentThread()
        counter = 0
        if config.performance_debug:
            t1 = time.time()
        while self.__wakeup:
            # it may be possible that a render or layout call triggers
            # rendering or layout again. We count this calls and
            # respect them up to five times. If the counter is higher,
            # there is an error in the programming logic and it could
            # be possible that this while loop goes on forever. To
            # prevent that, we stop with an error.
            self.__wakeup = False
            counter += 1
            if counter == 5:
                log.error('Syncing the stage triggers sync again for five times.')
                break
            try:
                if self._sync_rendering:
                    self._candy_prepare()
                    self._sync_rendering = False
                    self._clutter_render()
                if self._sync_layout:
                    self._clutter_sync_layout()
                if self._sync_properties:
                    self._clutter_sync_properties()
                    self._sync_properties = {}
            except Exception, e:
                log.exception('kaa.candy.sync')
                break
        if config.performance_debug:
            diff = time.time() - t1
            if diff > 0.05:
                log.warning('candy_sync() took %2.3f secs' % diff)
        if event:
            event.set()
        return False

    def _clutter_render(self):
        """
        Render the widget. This will only be called on stage creation
        """
        if not self._obj:
            self._obj = backend.Stage()
            self._obj.set_size(self.width, self.height)
            self._obj.connect('key-press-event', self._clutter_handle_key)
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
        super(Stage, self)._clutter_render()
