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

    def __init__(self, pos, size, font, color, text, context=None):
        """
        Create a new label widget

        @param pos: (x,y) position of the widget or None
        @param size: (width,height) geometry of the widget. The height
            parameter is used for vertical alignment and can be None.
        @param font: kaa.candy.Font object
        @param text: Text to render. This can also be a context based string like
            C{$text} with the context containing C{text='My String'}. This will
            make the widget context sensitive.
        @param context: the context the widget is created in
        """
        if size[1] is None:
            size = size[0], font.get_height(font.MAX_HEIGHT)
        super(Label, self).__init__(pos, size, context)
        self.font = font
        self.text = text
        self.color = color

    def set_context(self, context):
        """
        Set a new context.

        @param context: dict of context key,value pairs
        """
        super(Label, self).set_context(context)
        # trigger new context evaluation
        self.text = self.__text

    @property
    def text(self):
        return self.__text

    @text.setter
    def text(self, text):
        self.__text = text
        def replace_context(matchobj):
            return self.eval_context(matchobj.groups()[0], depends=False)
        if self.get_context():
            # we have a context, use it
            text = re.sub('\$([a-zA-Z_\.]*)', replace_context, text)
        if self.__text_eval != text:
            self.__text_eval = text
            self._queue_sync(rendering=True)

    @property
    def color(self):
        return self.__color

    @color.setter
    def color(self, color):
        if not isinstance(color, Color):
            color = Color(color)
        self.__color = color
        self._queue_sync(rendering=True)

    @property
    def font(self):
        return self.__font

    @font.setter
    def font(self, font):
        if not isinstance(font, Font):
            font = Font(font)
        self.__font = font
        self._queue_sync(rendering=True)
        if self._obj is not None:
            height = font.get_height(font.MAX_HEIGHT)
            if self.height < height:
                log.warning('adjusting Label.height because of font change')
                self.height = height

    def _candy_render(self):
        """
        Render the widget
        """
        fade = False
        width = self.__font.get_width(self.__text_eval)
        height = self.__font.get_height(Font.MAX_HEIGHT)
        if width > self.width:
            fade = True
            width = self.width
        if self._obj is None:
            self._obj = backend.CairoTexture(width, height)
            self._obj.show()
        else:
            if width != self._obj.get_width() or height != self._obj.get_height():
                self._obj.set_size(width, height)
                self._obj.surface_resize(width, height)
            self._obj.clear()
        # draw new text string
        context = self._obj.cairo_create()
        context.set_operator(cairo.OPERATOR_SOURCE)
        context.set_source_rgba(*self.__color.to_cairo())
        context.select_font_face(self.__font.name, cairo.FONT_SLANT_NORMAL)
        context.set_font_size(self.__font.size)
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

    @classmethod
    def candyxml_parse(cls, element):
        """
        Parse the candyxml element for parameter to create the widget. Example::
          <label y='50' width='100' font='Vera:24' color='0xffffffff'>
              <properties align='center,top'/>
              text to show
          </label>
        The text can also be a context based variable like C{$text}. This
        will make the widget context sensitive.
        """
        return super(Label, cls).candyxml_parse(element).update(
            font=element.font, color=element.color, text=element.content)


# register widget to candyxml
Label.candyxml_register()
