# -*- coding: iso-8859-1 -*-
# -----------------------------------------------------------------------------
# reflection - Reflection texture based on CairoTexture
# -----------------------------------------------------------------------------
# $Id: __init__.py 3369 2008-07-17 19:51:56Z dmeyer $
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

# clutter imports
import clutter
import gtk
import cairo

# backend imports
from ..backend import CairoTexture

class CairoReflectTexture(CairoTexture):
    """
    Reflection texture based on CairoTexture
    """
    def __init__(self, texture, height=0.5, opacity=0.8):
        size = (1,1)
        # FIXME: clutter 0.8 does not support get_pixbuf()
        pixbuf = texture.get_pixbuf()
        if pixbuf:
            size = pixbuf.get_width(), pixbuf.get_height()
        super(CairoReflectTexture, self).__init__(*size)
        self._reflection_height = height
        self._opacity = opacity
        # FIXME: check for memory leak
        texture.connect('pixbuf-change', self._update)
        if pixbuf:
            self._render(texture)

    def _update(self, src):
        """
        Update the source texture
        """
        context = self.cairo_create()
        context.set_operator(cairo.OPERATOR_CLEAR)
        context.set_source_rgba(255,255,255,255)
        context.paint()
        del context
        self._render(src)

    def _render(self, src, pixbuf=None):
        """
        Render the reflection
        """
        if not pixbuf:
            # FIXME: maybe size is still correct
            pixbuf = src.get_pixbuf()
            self.surface_resize(pixbuf.get_width(), pixbuf.get_height())
        context = self.cairo_create()
        ct = gtk.gdk.CairoContext(context)

        # create gradient and use it as mask
        gradient = cairo.LinearGradient(0, 0, 0, pixbuf.get_height())
        gradient.add_color_stop_rgba(1 - self._reflection_height, 1, 1, 1, 0)
        gradient.add_color_stop_rgba(1, 0, 0, 0, self._opacity)
        ct.set_source_pixbuf(pixbuf, 0, 0)
        context.mask(gradient)

        # Update texture
        del context
        del ct

        # Rotate the reflection based on any rotations to the master
        ang_y = src.get_rotation(clutter.Y_AXIS)
        self.set_rotation(clutter.Y_AXIS, ang_y[0], (src.get_width()), 0, 0)
        ang_x = src.get_rotation(clutter.X_AXIS)
        self.set_rotation(clutter.X_AXIS, ang_x[0], 0, (src.get_height()), 0)

        (w, h) = src.get_size()
        self.set_width(w)
        self.set_height(h)

        # Flip it upside down
        self.set_anchor_point(0, h)
        self.set_rotation(clutter.X_AXIS, 180, 0, 0, 0)

        # Get/Set the location for it
        (x, y) = src.get_position()
        self.set_position(x, h+y)
