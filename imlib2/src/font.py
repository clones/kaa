# -*- coding: iso-8859-1 -*-
# -----------------------------------------------------------------------------
# font.py - An Imlib2 font class
# -----------------------------------------------------------------------------
# $Id$
# -----------------------------------------------------------------------------
# kaa.imlib2 - An imlib2 wrapper for Python
# Copyright (C) 2004-2006 Dirk Meyer, Jason Tackaberry
#
# First Edition: Jason Tackaberry <tack@urandom.ca>
# Maintainer:    Jason Tackaberry <tack@urandom.ca>
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

__all__ = [
    'add_font_path', 'load_font', 'auto_set_font_path', 'normalize_color',
    'get_font_style_geometry', 'Font',
    # TEXT_STYLE constants
    'TEXT_STYLE_PLAIN', 'TEXT_STYLE_SHADOW', 'TEXT_STYLE_OUTLINE',
    'TEXT_STYLE_SOFT_OUTLINE', 'TEXT_STYLE_GLOW', 'TEXT_STYLE_OUTLINE_SHADOW',
    'TEXT_STYLE_FAR_SHADOW', 'TEXT_STYLE_OUTLINE_SOFT_SHADOW',
    'TEXT_STYLE_SOFT_SHADOW', 'TEXT_STYLE_FAR_SOFT_SHADOW'
]

# python imports
import types
import os
try:
    from collections import namedtuple
except ImportError:
    # Python 2.5-
    namedtuple = None

# imlib2 wrapper
import _Imlib2
from kaa.utils import property
from kaa.strutils import utf8

TEXT_STYLE_PLAIN = 0
TEXT_STYLE_SHADOW = 1
TEXT_STYLE_OUTLINE = 2
TEXT_STYLE_SOFT_OUTLINE = 3
TEXT_STYLE_GLOW = 4
TEXT_STYLE_OUTLINE_SHADOW = 5
TEXT_STYLE_FAR_SHADOW = 6
TEXT_STYLE_OUTLINE_SOFT_SHADOW = 7
TEXT_STYLE_SOFT_SHADOW = 8
TEXT_STYLE_FAR_SOFT_SHADOW = 9

TEXT_STYLE_GEOMETRY = [
    (0,0,0,0,0,0), (0,0,1,1,1,1), (1,1,1,1,2,2), (2,2,2,2,4,4),
    (2,2,2,2,4,4), (1,1,2,2,3,3), (0,0,2,2,2,2), (1,1,4,4,5,5),
    (1,1,3,3,4,4), (0,0,4,4,4,4)
]

if namedtuple:
    font_style_geometry = namedtuple('font_style_geometry',
                                     'left, top, right, bottom, width, height')
else:
    font_style_geometry = None

def get_font_style_geometry(style):
    """
    Return the additional size in pixels needed for the given style.

    :param style: one of the TEXT_STYLE constants
    :returns: 6-tuple (left, top, right, bottom, width, height)

    Width and height are included as a convenience, but they are just
    the sum of left+right and top+bottom.

    On Python 2.6 and later this function will return a named tuple.
    """
    if font_style_geometry:
        return font_style_geometry(*TEXT_STYLE_GEOMETRY[style])
    return TEXT_STYLE_GEOMETRY[style]


def add_font_path(path):
    """
    Add the given path to the list of paths to scan when loading fonts.

    :param path: directory containing fonts
    :type path: str
    """
    _Imlib2.add_font_path(path)


def load_font(font, size):
    """
    Load a TrueType font from the first directory in the font path that
    contains the specified font.

    :param font: the name of the font to load, e.g. 'arial'
    :type font: str
    :param size: the size in pixels of the font 
    :raises: IOError if the font could not be loaded.
    :returns: :class:`~imlib2.Font` object
    """
    return Font(font + '/' + str(size))


def auto_set_font_path():
    """
    Automatically add to Imlib2's font path any directory known by
    FontConfig to contain TrueType fonts.

    .. warning::

       This function spawns ``fc-list`` which can take some time to execute
       with a cold cache.
    """
    seen = set()
    for line in os.popen('fc-list :fontformat=TrueType file 2>/dev/null'):
        path = os.path.dirname(line)
        if path not in seen:
            add_font_path(path)
            seen.add(path)


def normalize_color(code):
    """
    Convert an HTML-style color code or an RGB 3-tuple into a 4-tuple of
    integers.

    :param code: a color code in the form ``#rrggbbaa``, ``#rrggbb``,
                 ``#rgba`` or ``#rgb``, or a 3- or 4-tuple of integers
                 specifying (red, green, blue, alpha).
    :type code: str or 3- or 4-tuple
    :returns: a 4-tuple of integers from 0-255 representing red, green, blue
              and alpha channels; if alpha is not specified in the color
              code, 255 is assumed.
    """
    if isinstance(code, (list, tuple)):
        if len(code) == 4:
            return tuple(code)
        elif len(code) == 3:
            return tuple(code) + (255,)
    elif isinstance(code, basestring) and code.startswith('#'):
        try:
            val = int(code[1:], 16)
        except ValueError:
            pass
        else:
            if len(code) == 9:
                return (val & 0xff000000) >> 24, (val & 0xff0000) >> 16, (val & 0xff00) >> 8, val & 0xff
            elif len(code) == 7:
                return (val & 0xff0000) >> 16, (val & 0xff00) >> 8, val & 0xff, 255
            elif len(code) == 5:
                return (val & 0xf000) >> 8, (val & 0xf00) >> 4, (val & 0xf0), (val & 0xf) << 4
            elif len(code) == 4:
                return (val & 0xf00) >> 4, val & 0xf0, (val & 0xf) << 4, 255
    raise ValueError('Unsupported color format: ' + repr(code))




class Font(object):
    """
    Font class representing an Imlib2 Font object.  Font objects may be assigned
    to :class:`~imlib2.Image` objects via their :attr:`~imlib2.Image.font` property
    to control font, size, and style to :meth:`~imlib2.Image.draw_text` operations.

    :param fontdesc: a description of the font either in the form ``name/size``,
                     where name is the filename of a ``.ttf`` file in the
                     font path, or a tuple in the form ``('name', size)``.
    :type fontdesc: str or 2-tuple
    :param color: the default color for text rendered with this font, specified
                  as any value that could be passed by
                  :func:`~imlib2.normalize_color`.

    Font paths can be registered by calling :func:`~imlib2.add_font_path` or
    :func:`~imlib2.auto_set_font_path`.

    Once a Font object is instantiated the font name cannot be changed, however
    the size can be changed by adjusting the :attr:`~imlib2.Font.size` property.
    """
    def __init__(self, fontdesc, color='#ffff'):
        # Setting self.size will implicitly create the _font object.
        if isinstance(fontdesc, (list, tuple)):
            self._name, self.size = fontdesc
        else:
            self._name, self.size = fontdesc.split('/')

        self.set_style(TEXT_STYLE_PLAIN)
        self.color = color


    def __repr__(self):
        return "<kaa.imlib2.%s object '%s/%d' at 0x%x>" % \
               (self.__class__.__name__, self._name, self._size, id(self))


    # Functions for pickling.
    def __getstate__(self):
        return (self._name, self._size, self._color, self.style,
               self.shadow, self.outline, self.glow, self.glow2)

    def __setstate__(self, state):
        (self._name, self.size, self._color, self.style, 
         self.shadow, self.outline, self.glow, self.glow2) = state

        
    @property
    def name(self):
        """
        The file name of the font (without the ``.ttf`` extension), e.g. ``VeraBd``
        """
        return self._name


    @property
    def color(self):
        """
        A 4-tuple containing the red, green, blue, and alpha values from 0-255.

        This property may be set to any value accepted by
        :func:`~imlib2.normalize_color`, but it will always be converted to a
        4-tuple.
        """
        return self._color

    @color.setter
    def color(self, value):
        self._color = normalize_color(value)
        

    @property
    def size(self):
        """
        The size in pixels of the font.
        """
        return self._size

    @size.setter
    def size(self, value):
        if getattr(self, '_size', None) != int(value):
            self._size = int(value)
            self._font = _Imlib2.load_font('%s/%d' % (self._name, self._size))


    def get_text_size(self, text):
        """
        Calculate font metrics (size and advance) for the specified text when
        rendered by the current font.

        :param text: the text whose metrics to calculate
        :type text: str or unicode
        :returns: 4-tuple (width, height, horizontal advance, vertical advance)
        """
        w, h, h_adv, v_adv = self._font.get_text_size(utf8(text))
        # Include size of any styling.
        style_w, style_h = self.get_style_geometry()[-2:]
        return w + style_w, h + style_h, h_adv + style_w + v_adv + style_h


    def set_color(self, color):
        """
        Deprecated: use the :attr:`~imlib2.Font.color` property instead.
        """
        self.color = color


    def set_size(self, size):
        """
        Deprecated: use the :attr:`~imlib2.Font.size` property instead.
        """
        self.size = size


    def set_style(self, style, shadow='#000f', outline='#000f', glow='#000f', glow2='#000f'):
        """
        Set the default text style for future text rendered with this font.

        :param style: the text style
        :type style: a :ref:`TEXT_STYLE <textstyles>` constant
        :param shadow: color used for any shadow styles
        :param outline: color used for any outline styles
        :param glow: color used for :attr:`~imlib2.TEXT_STYLE_GLOW`
        :param glow2: color used for :attr:`~imlib2.TEXT_STYLE_GLOW`
        """
        self.style = style
        self.shadow = normalize_color(shadow)
        self.outline = normalize_color(outline)
        self.glow = normalize_color(glow)
        self.glow2 = normalize_color(glow2)


    def get_style_geometry(self):
        """
        Return the additional size in pixels needed for the current style.

        See :func:`~imlib2.get_font_style_geometry` for more details.
        """
        return get_font_style_geometry(self.style)


    @property
    def ascent(self):
        """
        The number of pixels from the baseline to the top of the text for
        nominal characters.
        """
        return self._font.ascent

    @property
    def descent(self):
        """
        The number of pixels from the baseline to the bottom of the text for
        nominal characters.
        """
        return self._font.descent

    @property
    def max_ascent(self):
        """
        The maximum ascent for all glyphs in the font.
        """
        return self._font.max_ascent

    @property
    def max_descent(self):
        """
        The maximum descent for all glyphs in the font.
        """
        return self._font.descent
