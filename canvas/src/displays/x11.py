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

__all__ = [ 'X11Canvas' ]

from kaa.canvas import Canvas
from kaa import display
from kaa import evas


class X11Canvas(Canvas):

    def __init__(self, size, use_gl = None, title = "Canvas"):
        self._window = display.X11Window(size = size, title = "Kaa Display Test")

        if use_gl == None:
            use_gl = "gl_x11" in evas.render_method_list() and \
                     self._window.get_display().glx_supported()

        self._canvas_window = display.EvasX11Window(use_gl, size = size, parent = self._window)
        self._canvas_window.show()
        super(X11Canvas, self).__init__()

        self["size"] = size
        
        self._wrap(self._canvas_window.get_evas())

        self._canvas_window.signals["key_press_event"].connect_weak(self.signals["key_press_event"].emit)
        # When main window gets first focus, pass have the evas window grab focus.
        self._window.signals["focus_in_event"].connect_weak_once(self._canvas_window.focus)
        self._window.signals["resize_event"].connect_weak(self._handle_resize_event)
        self._canvas_window.set_cursor_hide_timeout(1)


    def _handle_resize_event(self, old_size, size):
        self._canvas_window.resize(size)
        self._o.output_size_set(size)
        #self.resize(size)
        self._queue_render()

    def _set_property_visible(self, vis):
        # Delay window hide/show until next render, because we want the
        # the render to happen before the window gets shown.
        self._visibility_on_next_render = vis
        self._queue_render()
        self._set_property_generic("visible", vis)


    def _render(self):
        vis = self._visibility_on_next_render
        if vis == False:
            self._window.hide()
        regions = self._o.render()
        if vis == True:
            self._window.show()

        self._visibility_on_next_render = None
        if regions:
            self.signals["updated"].emit(regions)
        return regions

    def get_window(self):
        return self._window
