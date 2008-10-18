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

# python imports
import types

# imlib2 wrapper
import _Imlib2
from kaa.strutils import utf8

TEXT_STYLE_PLAIN, \
TEXT_STYLE_SHADOW, \
TEXT_STYLE_OUTLINE, \
TEXT_STYLE_SOFT_OUTLINE, \
TEXT_STYLE_GLOW, \
TEXT_STYLE_OUTLINE_SHADOW, \
TEXT_STYLE_FAR_SHADOW, \
TEXT_STYLE_OUTLINE_SOFT_SHADOW, \
TEXT_STYLE_SOFT_SHADOW, \
TEXT_STYLE_FAR_SOFT_SHADOW = range(10)

TEXT_STYLE_GEOMETRY = [
    (0,0,0,0,0,0), (0,0,1,1,1,1), (1,1,1,1,2,2), (2,2,2,2,4,4),
    (2,2,2,2,4,4), (1,1,2,2,3,3), (0,0,2,2,2,2), (1,1,4,4,5,5),
    (1,1,3,3,4,4), (0,0,4,4,4,4)
]

class Font(object):
    def __init__(self, fontdesc, color=(255,255,255,255)):
        """
        Create a new Font object.

        Arguments:
          fontdesc: the description of the font, in the form 'Fontname/Size'
                    or as a list/tuple in the form ('Fontname', size).
                    Only TrueType fonts are supported, and the .ttf file must
                    exist in a registered font path.  Font paths can be
                    registered by calling Imlib2.add_font_path().
             color: a 3- or 4-tuple holding the red, green, blue, and alpha
                    values of the color in which to render text with this
                    font context.  If color is a 3-tuple, the implied alpha
                    is 255.  If color is not specified, the default is fully
                    opaque white.
        """
        if isinstance(fontdesc, (list, tuple)):
            fontdesc = fontdesc[0] + '/' + str(fontdesc[1])
        self._font = _Imlib2.load_font(fontdesc)
        sep = fontdesc.index("/")
        self.fontname = fontdesc[:sep]
        self.size = fontdesc[sep + 1:]
        self.set_color(color)
        self.style = TEXT_STYLE_PLAIN


    def get_text_size(self, text):
        """
        Get the font metrics for the specified text as rendered by the
        current font. The given text is used to retrieve the
        metric. The functions returns a 4-tuple containing the width,
        height, horizontal advance, and vertical advance of the text
        when rendered.
        """
        return self._font.get_text_size(utf8(text))


    def set_color(self, color):
        """
        Sets the default color for text rendered with this font. Color
        is a 3- or 4-tuple holding the red, green, blue, and alpha
        values of the color in which to render text with this font
        context.  If color is a 3-tuple, the implied alpha is 255.
        """
        if len(color) == 3:
            self.color = tuple(color) + (255,)
        else:
            self.color = color


    def set_size(self, size):
        """
        Sets a new font size.
        """
        fontdesc = self.fontname + '/' + str(size)
        self._font = _Imlib2.load_font(fontdesc)
        self.size = int(size)


    def set_style(self, style, shadow=(0,0,0,0), outline=(0,0,0,0),
                  glow=(0,0,0,0), glow2=(0,0,0,0)):
        """
        Set a text style. Based on the style different color parameter
        need to be set. Depending on the style additional parameter
        must be set:

        * TEXT_STYLE_PLAIN
        * TEXT_STYLE_SHADOW, requires shadow
        * TEXT_STYLE_OUTLINE, requires outline
        * TEXT_STYLE_SOFT_OUTLINE, requires outline
        * TEXT_STYLE_GLOW, requires glow, glow2
        * TEXT_STYLE_OUTLINE_SHADOW, requires shadow, outline
        * TEXT_STYLE_FAR_SHADOW, requires shadow
        * TEXT_STYLE_OUTLINE_SOFT_SHADOW, requires shadow, outline
        * TEXT_STYLE_SOFT_SHADOW, requires shadow
        * TEXT_STYLE_FAR_SOFT_SHADOW, requires shadow
        """
        self.style = style
        if len(shadow) == 3:
            self.shadow = tuple(shadow) + (255,)
        else:
            self.shadow = shadow
        if len(outline) == 3:
            self.outline = tuple(outline) + (255,)
        else:
            self.outline = outline
        if len(glow) == 3:
            self.glow = tuple(glow) + (255,)
        else:
            self.glow = glow
        if len(glow2) == 3:
            self.glow2 = tuple(glow2) + (255,)
        else:
            self.glow2 = glow2


    def get_style_geometry(self):
        """
        Return the additional pixel the font needs for the style. This function
        will return left, top, right, bottom as number of pixels the text will
        start to the left/top and the number of pixels it needs more at the
        right/bottom. To avoid extra calculations the function will also return
        the additional width and height needed for the style.
        """
        return TEXT_STYLE_GEOMETRY[self.style]


    def __getattr__(self, attr):
        """
        These attributes are available:

               ascent: the current font's ascent value in pixels.
              descent: the current font's descent value in pixels.
          max_descent: the current font's maximum descent extent.
           max_ascent: the current font's maximum ascent extent.
        """
        if attr == "ascent":
            return self._font.ascent
        elif attr == "descent":
            return self._font.descent
        elif attr == "max_ascent":
            return self._font.max_ascent
        elif attr == "max_descent":
            return self._font.max_descent
        if attr not in self.__dict__:
            raise AttributeError, attr
        return self.__dict__[attr]
