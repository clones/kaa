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

# python imports
import logging
import cairo
import re

from kaa.utils import property

# kaa.candy imports
from ..core import Color, Font
from .. import backend
from widget import Widget

# get logging object
log = logging.getLogger('kaa.candy')


class Label(Widget):
    """
    Text label widget based on cairo.
    """
    candyxml_name = 'label'
    context_sensitive = True

    __text_eval = ''
    _regexp_eval = re.compile('\$([a-zA-Z][a-zA-Z0-9_\.]*)|\${([^}]*)}')

    def __init__(self, pos, size, text, font, color, context=None):
        """
        Create a new label widget

        @param pos: (x,y) position of the widget or None
        @param text: Text to render. This can also be a context based string like
            C{$text} with the context containing C{text='My String'}. This will
            make the widget context sensitive.
        @param size: (width,height) geometry of the widget.
        @param font: kaa.candy.Font object
        @param context: the context the widget is created in
        """
        super(Label, self).__init__(pos, size, context)
        self.font = font
        self.text = text
        self.color = color

    def _candy_context_sync(self, context):
        """
        Set a new context.

        @param context: dict of context key,value pairs
        """
        super(Label, self)._candy_context_sync(context)
        # trigger new context evaluation
        self.text = self.__text

    @property
    def text(self):
        return self.__text

    @text.setter
    def text(self, text):
        self.__text = text
        def replace_context(matchobj):
            match = matchobj.groups()[0] or matchobj.groups()[1]
            s = self.context.get(match, '')
            if s is not None:
                return unicode(s)
            return ''
        if self.context:
            # we have a context, use it
            text = re.sub(self._regexp_eval, replace_context, text)
        if self.__text_eval != text:
            self.__text_eval = text
            self._queue_rendering()

    @property
    def color(self):
        return self.__color

    @color.setter
    def color(self, color):
        if not isinstance(color, Color):
            color = Color(color)
        self.__color = color
        self._queue_rendering()

    @property
    def font(self):
        return self.__font

    @font.setter
    def font(self, font):
        if not isinstance(font, Font):
            font = Font(font)
        self.__font = font
        self._queue_rendering()
        if self._obj is not None:
            height = font.get_height(font.MAX_HEIGHT)
            if self.height < height:
                log.warning('adjusting Label.height because of font change')
                self.height = height

    def _clutter_render(self):
        """
        Render the widget
        """
        fade = False
        font = self.__font
        if font.size == 0:
            # get font based on widget height
            font = font.get_font(self.inner_height)

        width = font.get_width(self.__text_eval)
        height = font.get_height(Font.MAX_HEIGHT)

        if width > self.inner_width:
            fade = True
            width = self.inner_width
        if self._obj is None:
            self._obj = backend.CairoTexture(width, height)
            self._obj.show()
        else:
            if width != self._obj.get_width() or height != self._obj.get_height():
                self._clutter_set_obj_size(width, height)
                self._obj.surface_resize(int(width), int(height))
            self._obj.clear()
        # draw new text string
        context = self._obj.cairo_create()
        context.set_operator(cairo.OPERATOR_SOURCE)
        context.set_source_rgba(*self.__color.to_cairo())
        context.select_font_face(font.name, cairo.FONT_SLANT_NORMAL)
        context.set_font_size(font.size)
        if fade:
            s = cairo.LinearGradient(0, 0, width, 0)
            c = self.__color.to_cairo()
            s.add_color_stop_rgba(0, *c)
            # 50 pixel fading
            s.add_color_stop_rgba(1 - (50.0 / width), *c)
            s.add_color_stop_rgba(1, c[0], c[1], c[2], 0)
            context.set_source(s)
        context.move_to(0, context.font_extents()[0])
        context.show_text(self.__text_eval)
        self._intrinsic_size = width, height

    @classmethod
    def candyxml_parse(cls, element):
        """
        Parse the candyxml element for parameter to create the widget. Example::
          <label y='50' width='100' font='Vera:24' color='0xffffffff'>
              <properties xalign='center'/>
              text to show
          </label>
        The text can also be a context based variable like C{$text}. This
        will make the widget context sensitive.
        """
        return super(Label, cls).candyxml_parse(element).update(
            font=element.font, color=element.color, text=element.content)
