# -*- coding: iso-8859-1 -*-
# -----------------------------------------------------------------------------
# rectangle.py - Rectange Widget
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

from kaa.utils import property

# kaa.candy imports
from ..core import Color
from image import CairoTexture

class Rectangle(CairoTexture):
    """
    Rectange with border and round corners based on cairo.
    """
    candyxml_name = 'rectangle'

    def __init__(self, pos, size, color=None, border_size=0,
                 border_color=None, radius=0):
        """
        Create a Rectange widget

        @param pos: (x,y) position of the widget or None
        @param size: (width,height) geometry of the widget.
        @param color: kaa.candy.Color to fill the rectangle
        @param border_size: size of the rectangle border
        @param border_color: kaa.candy.Color of the border. This argument is
            not needed when border_size is 0.
        @param radius: radius for a rectangle with round edges.
        """
        super(Rectangle, self).__init__(pos, size)
        if color and not isinstance(color, Color):
            color = Color(color)
        if border_color and not isinstance(border_color, Color):
            border_color = Color(border_color)
        self.__color = color
        self.__radius = radius
        self.__border_size = border_size
        self.__border_color = border_color

    @property
    def color(self):
        return self.__color

    @color.setter
    def color(self, color):
        if color and not isinstance(color, Color):
            color = Color(color)
        self.__color = color
        self._queue_sync(rendering=True)

    @property
    def border_size(self):
        return self.__border_size

    @border_size.setter
    def border_size(self, size):
        self.__border_size = size
        self._queue_sync(rendering=True)

    @property
    def border_color(self):
        return self.__border_color

    @border_color.setter
    def border_color(self, color):
        if color and not isinstance(color, Color):
            color = Color(color)
        self.__border_color = color
        self._queue_sync(rendering=True)

    @property
    def radius(self):
        return self.__radius

    @radius.setter
    def radius(self, radius):
        self.__radius = radius
        self._queue_sync(rendering=True)

    def _candy_render(self):
        """
        Render the widget
        """
        super(Rectangle, self)._candy_render()
        context = self._obj.cairo_create()

        if not self.__border_size and not self.__radius:
            # A simple fill on the surface. Using clutter.Rectangle
            # would be faster here but we do not need that much normal
            # rectangles and it would make things more complicated
            context.set_source_rgba(*self.__color.to_cairo())
            context.paint()
            return

        stroke = self.__border_size or 1
        width  = self.inner_width - 2 * stroke
        height = self.inner_height - 2 * stroke
        radius = min(self.__radius, width, height)

        x0 = stroke
        y0 = stroke
        x1 = x0 + width
        y1 = y0 + height

        if self.__color:
            context.set_source_rgba(*self.__color.to_cairo())
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

        if self.__border_size and self.__border_color:
            context.set_source_rgba(*self.__border_color.to_cairo())
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
    def candyxml_parse(cls, element):
        """
        Parse the candyxml element for parameter to create the widget. Example::
            <rectangle x='0' y='0' width='100' height='100' color='0xff0000'
                border_size='2' border_color='0x000000' radius='10'/>
        """
        return super(Rectangle, cls).candyxml_parse(element).update(
            radius=int(element.radius or 0), border_size=float(element.border_size or 0),
            color=element.color, border_color=element.border_color)


# register widget to candyxml
Rectangle.candyxml_register()
