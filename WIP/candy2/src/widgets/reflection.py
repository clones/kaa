# -*- coding: iso-8859-1 -*-
# -----------------------------------------------------------------------------
# reflection.py - Reflection Widget
# -----------------------------------------------------------------------------
# $Id$
#
# This class is completly broken. To test it, run flickr2.py in test
#
# You can see one bug here. Reflection does not describe a reflection, it
# describes a texture _and_ its reflection. You also have to set the height
# to something larger than the cell height to have the image which has a smaller
# height still fit nicly in the cell. The height for reflection is the height
# of both objects.
#
# A second bug is that this widget sets the anchor point and this changes
# the x and y coordinates of the widget. kaa.candy MUST deal with this somehow,
# other widgets may do the same. So set_y will not do what you expect it to do,
# only relative moves work.
#
# And the last bug: I have no idea how to control the gradient effect. Changing
# some variables do not have the effect I think it should have
# http://cairographics.org/manual/cairo-Patterns.html#cairo-pattern-add-color-stop-rgba
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
import core

__all__ = [ 'Reflection' ]

class ReflectionTexture(core.CairoTexture):

    def __init__(self, texture):
        super(ReflectionTexture, self).__init__(None, (1, 1))
        # FIXME: check for memory leak
        texture.connect('pixbuf-change', self.update)
        if texture.get_pixbuf():
            self.update(texture)

    def update(self, src):
        self.clear()
        pixbuf = src.get_pixbuf()
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


class Reflection(core.Group):
    """
    Widget with child and its reflection (broken)
    @bug: this code is broken
    """
    candyxml_name = 'reflection'
    context_sensitive = True

    def __init__(self, pos, size, texture, context=None):
        super(Reflection, self).__init__(pos, size, context)
        texture_height = int(size[1] / 1.8)
        # set anchor point to the center
        self.set_anchor_point(size[0]/2, texture_height)
        self.move_by(size[0]/2, texture_height)
        texture = texture(context, x=0, y=0, width=size[0], height=texture_height)
        self.add(texture)
        self._depends = texture._depends
        self.reflection = ReflectionTexture(texture)
        self.reflection.set_opacity(50)
        self.reflection.set_parent(self)

    @classmethod
    def candyxml_parse(cls, element):
        """
        Parse the candyxml element for parameter to create the widget. No example
        yet, the code is broken.
        """
        return super(Reflection, cls).candyxml_parse(element).update(
            texture=element.get_children()[0].xmlcreate())

# register widget to the core
Reflection.candyxml_register()
