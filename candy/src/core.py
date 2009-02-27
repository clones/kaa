# -*- coding: iso-8859-1 -*-
# -----------------------------------------------------------------------------
# core.py - Helper classes and decorator
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

__all__ = [ 'is_template', 'Context', 'Color', 'Font', 'Modifier', 'Properties' ]

# python imports
import logging
import cairo

# get logging object
log = logging.getLogger('kaa.candy')

def is_template(obj):
    """
    Returns True if the given object is a kaa.candy template class. This function
    is needed to check if a given widget is a real clutter widget or only a template
    for creating one.
    """
    return getattr(obj, '__is_template__', False)


class Context(dict):

    def __init__(self, ctx):
        super(Context, self).__init__(ctx.copy())

    def get(self, attr, default=None):
        if attr.startswith('$'):
            # strip prefix for variables if set
            attr = attr[1:]
        try:
            # try the variable as it is
            value = eval(attr, self)
            return value
        except Exception, e:
            log.error('unable to evaluate %s', attr)
            return default

    def __getattr__(self, attr):
        return self.get(attr)

class Color(list):
    """
    Color object which is a list of r,g,b,a with values between 0 and 255.
    """
    def __init__(self, *col):
        """
        Create a new color object. All C{set_color} member functions of kaa.candy
        widgets use this class for setting a color and not the clutter color object.
        The Color object is list of r,g,b,a with values between 0 and 255.

        @param col: one of the following types
         - a tuple r,g,b,a
         - a clutter color object
         - a string #aarrggbb
        """
        if len(col) > 1:
            return super(Color, self).__init__(col)
        col = col[0]
        if col == None:
            return super(Color, self).__init__((0,0,0,255))
        if hasattr(col, 'red'):
            # clutter.Color object
            return super(Color, self).__init__((col.red, col.green, col.blue, col.alpha))
        if isinstance(col, (list, tuple)):
            # tuple as one argument
            return super(Color, self).__init__(col)
        # Convert a 32-bit ARGB string 0xaarrggbb
        if not isinstance(col, (int, long)):
            col = long(col, 16)
        a = 255 - ((col >> 24) & 0xff)
        r = (col >> 16) & 0xff
        g = (col >> 8) & 0xff
        b = (col >> 0) & 0xff
        super(Color, self).__init__((r,g,b,a))

    def to_cairo(self):
        """
        Convert to list used by cairo.

        @returns: list with float values from 0 to 1.0
        """
        return [ x / 255.0 for x in self ]


class Font(object):
    """
    Font object containing font name and font size

    @ivar name: font name
    @ivar size: font size
    """

    __cairo_surface = None
    __height_cache = {}

    ASCENT, TYPICAL, MAX_HEIGHT = range(3)

    def __init__(self, name):
        """
        Create a new font object
        @param name: name and size of the font, e.g. Vera:24
        """
        self.name = name
        self.size = 0
        if name.find(':') > 0:
            self.name, size = name.split(':')
            self.size = int(size)

    def get_height(self, field=None, size=None):
        """
        Get height of a text with this font.
        @returns: ascent (typical height above the baseline), normal (typical height
            of a string without special characters) and ascent + descent
        """
        if size is None:
            size = self.size
        info = self.__height_cache.get((self.name, size))
        if info is None:
            if self.__cairo_surface is None:
                self.__cairo_surface = cairo.ImageSurface(cairo.FORMAT_ARGB32, 10, 10)
            c = cairo.Context(self.__cairo_surface)
            c.select_font_face(self.name, cairo.FONT_SLANT_NORMAL)
            c.set_font_size(size)
            ascent, descent = c.font_extents()[:2]
            info = int(ascent), int(-c.text_extents(u'Ag')[1]), int(ascent + descent)
            self.__height_cache[(self.name, size)] = info
        if field is None:
            return info
        return info[field]

    def get_width(self, text):
        """
        Get width of the given string
        """
        if self.__cairo_surface is None:
            self.__cairo_surface = cairo.ImageSurface(cairo.FORMAT_ARGB32, 10, 10)
        c = cairo.Context(self.__cairo_surface)
        c.select_font_face(self.name, cairo.FONT_SLANT_NORMAL)
        c.set_font_size(self.size)
        # add x_bearing to width (maybe use x_advance later)
        # http://cairographics.org/manual/cairo-Scaled-Fonts.html#cairo-text-extents-t
        ext = c.text_extents(text)
        return int(ext[0] + ext[2]) + 1

    def get_font(self, height):
        """
        Get font object with size set to fit the given height.
        """
        size = 1
        last = None
        while True:
            if not self.__height_cache.get((self.name, size)):
                self.get_height(size=size)
            if self.__height_cache.get((self.name, size))[Font.MAX_HEIGHT] > height:
                f = Font(self.name)
                f.size = size
                return f
            last = size
            size += 1


class Modifier(object):
    """
    Modifier base class for classes that change widgets on creation by
    templates. In the XML file they are added as subnode to the widget
    to change. Examples are Properties and ReflectionModifier.
    """

    class __metaclass__(type):
        def __new__(meta, name, bases, attrs):
            cls = type.__new__(meta, name, bases, attrs)
            if 'candyxml_name' in attrs.keys():
                if cls.candyxml_name in Modifier._candyxml_modifier:
                    raise RuntimeError('%s already defined' % cls.candyxml_name)
                Modifier._candyxml_modifier[cls.candyxml_name] = cls
            return cls

    _candyxml_modifier = {}

    def modify(self, widget):
        """
        Modify the given widget.
        @param widget: widget to modify
        @returns: changed widget (may be the same)
        """
        raise NotImplementedError

    @classmethod
    def candyxml_create(cls, element):
        """
        Create the modifier for the given element.

        @note: do not call this function from inheriting functions. The name
            is the same but the logic is different. This functions calls the
            implementation variant, not the other way around.
        """
        cls = Modifier._candyxml_modifier.get(element.node)
        if cls is None:
            return cls
        return cls.candyxml_create(element)


class Properties(dict, Modifier):
    """
    Properties class to apply the given properties to a widget. This is a
    dictionary for clutter functions to call after the widget is created.
    It is used by candyxml and the animation submodule.
    """

    #: candyxml name
    candyxml_name = 'properties'

    def modify(self, widget):
        """
        Apply to the given widget.

        @param widget: a kaa.candy.Widget
        """
        for key, value in self.items():
            setattr(widget, key, value)
        return widget

    @classmethod
    def candyxml_create(cls, element):
        """
        Parse the candyxml element and create a Properties object::

          <widget_or_animation>
            <properties key=value key=value>
          </widget_or_animation>

        Possible keys are C{opacity} (int), C{depth} (int),
        C{scale} (float,float), C{anchor_point} (float,float)
        """
        properties = cls()
        for key, value in element.attributes():
            if key in ('opacity', 'depth'):
                value = int(value)
            elif key in ('rotation','xrotation','yrotation','zrotation'):
                value = float(value)
            elif key in ('xalign', 'yalign'):
                value = value.lower()
            elif key in ('keep_aspect', 'passive'):
                value = value.lower() in ('yes', 'true')
            elif key in ('scale','anchor_point'):
                value = [ float(x) for x in value.split(',') ]
                value = int(value[0] * element.get_scale_factor()[0]), \
                        int(value[1] * element.get_scale_factor()[1])
            properties[key] = value
        return properties
