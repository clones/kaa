# -*- coding: iso-8859-1 -*-
# -----------------------------------------------------------------------------
# font.py - An Imlib2 font class
# -----------------------------------------------------------------------------
# $Id$
# -----------------------------------------------------------------------------
# Copyright (C) 2004-2005 Jason Tackaberry <tack@sault.org>
#
# Maintainers: Jason Tackaberry <tack@sault.org>
#              Dirk Meyer <dmeyer@tzi.de>
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful, but
# WITHOUT ANY WARRANTY; without even the implied warranty of MER-
# CHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the GNU General
# Public License for more details.
#
# You should have received a copy of the GNU General Public License along
# with this program; if not, write to the Free Software Foundation, Inc.,
# 59 Temple Place, Suite 330, Boston, MA 02111-1307 USA
#
# -----------------------------------------------------------------------------

# python imports
import types

# imlib2 wrapper
import _Imlib2
from kaa.strutils import utf8

class Font(object):
    def __init__(self, fontdesc, color=(255,255,255,255)):
        """
        Create a new Font object.

        Arguments:
          fontdesc: the description of the font, in the form 'Fontname/Size'.
                    Only TrueType fonts are supported, and the .ttf file must
                    exist in a registered font path.  Font paths can be
                    registered by calling Imlib2.add_font_path().
             color: a 3- or 4-tuple holding the red, green, blue, and alpha
                    values of the color in which to render text with this
                    font context.  If color is a 3-tuple, the implied alpha
                    is 255.  If color is not specified, the default is fully
                    opaque white.
        """

        self._font = _Imlib2.load_font(fontdesc)
        sep = fontdesc.index("/")
        self.fontname = fontdesc[:sep]
        self.size = fontdesc[sep + 1:]
        self.set_color(color)
        self.style = 0 # TEXT_STYLE_PLAIN
        

    def get_text_size(self, text):
        """
        Get the font metrics for the specified text as rendered by the
        current font.

        Arguments:
          text: the text for which to retrieve the metric.

        Returns: a 4-tuple containing the width, height, horizontal advance,
                 and vertical advance of the text when rendered.
        """
        return self._font.get_text_size(utf8(text))


    def set_color(self, color):
        """
        Sets the default color for text rendered with this font.

        Arguments:
            color: a 3- or 4-tuple holding the red, green, blue, and alpha
                   values of the color in which to render text with this
                   font context.  If color is a 3-tuple, the implied alpha
                   is 255.
        """
        if len(color) == 3:
            self.color = tuple(color) + (255,)
        else:
            self.color = color


    def set_style(self, style, shadow=(0,0,0,0), outline=(0,0,0,0),
                  glow=(0,0,0,0), glow2=(0,0,0,0)):
        """
        Set a text style. Based on the style different color parameter
        need to be set.

        Arguments:
            style:   the style to use (disable with TEXT_STYLE_PLAIN)
            shadow:  shadow color for TEXT_STYLE_SHADOW, TEXT_STYLE_OUTLINE_SHADOW,
                     TEXT_STYLE_FAR_SHADOW, TEXT_STYLE_OUTLINE_SOFT_SHADOW,
                     TEXT_STYLE_SOFT_SHADOW and TEXT_STYLE_FAR_SOFT_SHADOW
            outline: outline color for TEXT_STYLE_OUTLINE, TEXT_STYLE_SOFT_OUTLINE, 
                     TEXT_STYLE_OUTLINE_SHADOW and TEXT_STYLE_OUTLINE_SOFT_SHADOW
            glow:    glow color 1 for TEXT_STYLE_GLOW
            glow2:   glow color 2 for TEXT_STYLE_GLOW
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
