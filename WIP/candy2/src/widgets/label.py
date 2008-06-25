# -*- coding: iso-8859-1 -*-
# -----------------------------------------------------------------------------
# label.py - Label Widget
# -----------------------------------------------------------------------------
# $Id$
#
# This code is much faster than the pango based code
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

# python imports
import cairo
import re

# kaa.candy imports
import core


class Label(core.CairoTexture):
    """
    Text label widget based on cairo.
    """
    candyxml_name = 'label'
    context_sensitive = True
    _font_instance = None
    _font_cache = {}

    def __init__(self, pos, size, font, color, text, align='left',
                 context=None):
        depends = []
        if context:
            def replace_context(matchobj):
                if not matchobj.groups()[0] in depends:
                    depends.append(matchobj.groups()[0])
                return eval(matchobj.groups()[0], context)
            text = re.sub('\$([a-zA-Z_\.]*)', replace_context, text)
        if size[1] is None:
            size = size[0], Label.get_font_height(font.name, font.size)[2]
        super(Label, self).__init__(pos, size, context)
        self.set_dependency(*depends)
        self._font = font
        self._color = color
        self._text = text
        self._align = align
        self._render()

    def set_color(self, color):
        """
        Set a new color
        """
        self._color = color
        self._render()

    def get_color(self):
        """
        Return color object.
        """
        return self._color

    @classmethod
    def get_font_height(cls, name, size):
        info = cls._font_cache.get((name, size))
        if info:
            return info
        if cls._font_instance is None:
            cls._font_instance = core.CairoTexture(None, (200,200))
        c = cls._font_instance.cairo_create()
        c.select_font_face(name, cairo.FONT_SLANT_NORMAL)
        c.set_font_size(size)
        extents = c.font_extents()
        info = extents[0], -c.text_extents('ARG:FIXME')[1], extents[0] + extents[1]
        cls._font_cache[(name, size)] = info
        return info

    def _render(self):
        """
        Render the text.
        """
        try:
            self.clear()
            # draw new text string
            context = self.cairo_create()
        except cairo.Error, e:
            # surface already gone
            return
        context.set_operator(cairo.OPERATOR_SOURCE)
        context.set_source_rgba(*self._color.to_cairo())
        context.select_font_face(self._font.name, cairo.FONT_SLANT_NORMAL)
        context.set_font_size(self._font.size)
        x, y, w, h = context.text_extents(self._text)[:4]
        # http://www.tortall.net/mu/wiki/CairoTutorial
        if self._align == 'left':
            x = -x
        if self._align == 'center':
            x = (self.get_property('surface_width') - w) / 2 - x
        if self._align == 'right':
            x = self.get_property('surface_width') - w - x
        if x < 0:
            x = 0
            w = self.get_property('surface_width')
            s = cairo.LinearGradient(0, 0, w, 0)
            c = self._color.to_cairo()
            s.add_color_stop_rgba(0, *c)
            # 50 pixel fading
            s.add_color_stop_rgba(1 - (50.0 / w), *c)
            s.add_color_stop_rgba(1, c[0], c[1], c[2], 0)
            context.set_source(s)
        context.move_to(x, context.font_extents()[0])
        context.show_text(self._text)
        #del context

    @classmethod
    def candyxml_parse(cls, element):
        """
        Parse the XML element for parameter to create the widget.
        """
        return super(Label, cls).candyxml_parse(element).update(
            font=element.font, color=element.color,
            text=element.content, align=element.align)


# register widget to the xmlparser
Label.candyxml_register()
