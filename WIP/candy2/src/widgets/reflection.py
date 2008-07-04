# -*- coding: iso-8859-1 -*-
# -----------------------------------------------------------------------------
# reflection.py - Reflection Widget
# -----------------------------------------------------------------------------
# $Id$
#
# BUG: I have no idea how to control the gradient effect. Changing some variables
# does not have the effect I think it should have
# http://cairographics.org/manual/cairo-Patterns.html
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
import gtk
import cairo
import clutter

# kaa.candy imports
from .. import Modifier
import core

__all__ = [ 'ReflectionTexture', 'ReflectionModifier' ]

class ReflectionTexture(core.CairoTexture):
    """
    Texture to show a reflection of another texture. This widget only works
    for Texture based widgets and uses software rendering.
    @param texture: source texture to reflect
    @todo: use GL based implementation
    """
    def __init__(self, texture):
        # FIXME: use correct height for valid texture
        super(ReflectionTexture, self).__init__(None, (1, 1))
        # FIXME: check for memory leak
        texture.connect('pixbuf-change', self._update)
        if texture.get_pixbuf():
            self._render(texture)

    def _update(self, src):
        """
        Update the source texture
        """
        self.clear()
        self._render(src)

    def _render(self, src):
        """
        Render the reflection
        """
        pixbuf = src.get_pixbuf()
        # FIXME: maybe size is correct
        self.surface_resize(pixbuf.get_width(), pixbuf.get_height())
        context = self.cairo_create()
        ct = gtk.gdk.CairoContext(context)
        gradient = cairo.LinearGradient(0, 0, 0, src.get_height())

        # FIXME: I have no idea what these two lines. At least playing
        # with the values does not do what I think it should do. But
        # maybe using cairo here is a bad idea in general, there is
        # a tidy actor in clutter for this, maybe that will work (at it
        # will use GL, always better than software rendering)
        gradient.add_color_stop_rgba(0.5, 1, 1, 1, 0)
        gradient.add_color_stop_rgba(1, 0, 0, 0, 0.8)

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


class ReflectionModifier(Modifier):
    """
    Modifier to add a reflection.
    """

    candyxml_name = 'reflection'

    def __init__(self, opacity=50):
        """
        Create modifier
        @param opacity: opacity of the reflection
        """
        self._opacity = opacity

    def modify(self, widget):
        """
        Modify the given widget.
        @param widget: widget to modify
        @returns: Group widget with src and reflection textures
        """
        w, h = widget.get_size()
        group = core.Group(widget.get_position(), (w,h))
        group.set_anchor_point(w/2, h)
        group.move_by(w/2, h)
        group.context_sensitive = True
        group._depends = widget._depends
        widget.set_position(0,0)
        widget.set_parent(group)
        reflection = ReflectionTexture(widget)
        reflection.set_opacity(self._opacity)
        reflection.set_parent(group)
        return group

    @classmethod
    def candyxml_create(cls, element):
        """
        Parse the candyxml element and create the modifier. Any texture based
        widget can be used as base. Example::
          <image width='100' height='100'>
              <reflection opacity='50'/>
          </image>
        """
        return cls(opacity = int(element.opacity or 50))

# register widget to the core
ReflectionModifier.candyxml_register()
