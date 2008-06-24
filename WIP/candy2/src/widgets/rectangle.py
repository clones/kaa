# -*- coding: iso-8859-1 -*-
# -----------------------------------------------------------------------------
# rectangle.py - Rectange Widgets
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

# kaa.candy imports
import kaa.candy
import core

class Rectangle(core.CairoTexture):
    """
    Rectange with border and round corners based on cairo.
    """
    __gui_name__ = 'rectangle'

    def __init__(self, pos, size, color=None, border_size=0,
                 border_color=None, radius=0):
        super(Rectangle, self).__init__(pos, size)
        self._radius = radius
        self._color = color
        self._border_size = border_size
        self._border_color = border_color
        self._render()

    def _render(self):
        """
        Render the rectangle.
        """
        context = self.cairo_create()

        if not self._border_size and not self._radius:
            # A simple fill on the surface. Using clutter.Rectangle
            # would be faster here but we do not need that much normal
            # rectangles and it would make things more complicated with two
            # widgets having the same name.
            context.set_source_rgba(*self._color.to_cairo())
            context.paint()
            return

        stroke = self._border_size or 1
        width  = self.get_property('surface_width') - 2 * stroke
        height = self.get_property('surface_height') - 2 * stroke
        radius = min(self._radius, width, height)

        x0 = stroke
        y0 = stroke
        x1 = x0 + width
        y1 = y0 + height

        if self._color:
            context.set_source_rgba(*self._color.to_cairo())
            context.set_line_width(stroke)
            context.move_to  (x0, y0 + radius)
            context.curve_to (x0, y0, x0 , y0, x0 + radius, y0)
            context.line_to (x1 - radius, y0)
            context.curve_to (x1, y0, x1, y0, x1, y0 + radius)
            context.line_to (x1 , y1 - radius)
            context.curve_to (x1, y1, x1, y1, x1 - radius, y1)
            context.line_to (x0 + radius, y1)
            context.curve_to (x0, y1, x0, y1, x0, y1- radius)
            context.close_path()
            context.fill()

        if self._border_size and self._border_color:
            context.set_source_rgba(*self._border_color.to_cairo())
            context.set_line_width(stroke)
            context.move_to  (x0, y0 + radius)
            context.curve_to (x0 , y0, x0 , y0, x0 + radius, y0)
            context.line_to (x1 - radius, y0)
            context.curve_to (x1, y0, x1, y0, x1, y0 + radius)
            context.line_to (x1 , y1 - radius)
            context.curve_to (x1, y1, x1, y1, x1 - radius, y1)
            context.line_to (x0 + radius, y1)
            context.curve_to (x0, y1, x0, y1, x0, y1- radius)
            context.close_path()
            context.stroke()

        del context

    @classmethod
    def parse_XML(cls, element):
        """
        Parse the XML element for parameter to create the widget.
        """
        return super(Rectangle, cls).parse_XML(element).update(
            radius=int(element.radius or 0), border_size=float(element.border_size or 0),
            color=element.color, border_color=element.border_color)
        
# register widgets to the core
kaa.candy.xmlparser.register(Rectangle)
