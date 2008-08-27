# -*- coding: iso-8859-1 -*-
# -----------------------------------------------------------------------------
# text.py - Text Widget
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

# python imports
import re

import pango

from kaa.utils import property

# kaa.candy imports
from ..core import Color, Font
from .. import backend
from widget import Widget


class Text(Widget):
    """
    Complex text widget.
    """
    candyxml_name = 'text'
    context_sensitive = True

    _regexp_space = re.compile('[\n\t \r][\n\t \r]+')
    _regexp_if = re.compile('#if(.*?):(.*?)#fi ?')
    _regexp_eval = re.compile('\$([a-zA-Z][a-zA-Z0-9_\.]*)|\${([^}]*)}')
    _regexp_br = re.compile(' *<br/> *')

    __text = __text_eval = ''
    __color = None

    def __init__(self, pos, size, text, font, color, align=None, context=None):
        """
        Create Text widget. Unlike a Label a Text widget supports multi-line
        text and markup. See the pango markup documentation.

        @note: setting yalign on a Text widget as no effect

        @param pos: (x,y) position of the widget or None
        @param size: (width,height) geometry of the widget
        @param text: text to show
        @param color: kaa.candy.Color to fill the text
        @param align: xalign value, convenience to set Text.xalign
        @param context: the context the widget is created in
        """
        super(Text, self).__init__(pos, size, context)
        self.xalign = align
        self.font = font
        self.text = text
        self.color = color

    def _set_context_execute(self, context):
        """
        Set a new context.

        @param context: dict of context key,value pairs
        """
        super(Text, self)._set_context_execute(context)
        # trigger new context evaluation
        self.text = self.__text

    @property
    def text(self):
        return self.__text

    @text.setter
    def text(self, text):
        self.__text = text
        def eval_expression(matchobj):
            if self.context.get(matchobj.groups()[0], default=''):
                return unicode(matchobj.groups()[1])
            return ''
        def replace_context(matchobj):
            # FIXME: maybe the string has markup to use
            match = matchobj.groups()[0] or matchobj.groups()[1]
            s = self.context.get(match, default='')
            if s is None:
                return ''
            return unicode(s).replace('&', '&amp;').replace('<', '&lt;').\
                   replace('>', '&gt;')
        if self.context:
            # we have a context, use it
            text = self._regexp_space.sub(' ', text)
            text = self._regexp_if.sub(eval_expression, text)
            text = self._regexp_eval.sub(replace_context, text).strip()
        text = self._regexp_br.sub('\n', text)
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

    def _candy_render(self):
        """
        Render the widget
        """
        if not self._obj:
            self._obj = backend.Label()
            self._obj.show()
            self._obj.set_size(self.inner_width, self.inner_height)
            # FIXME: bad style, see if clutter 0.8 makes it possible to cut the
            # text. PangoLayout seems to have a set_height function but I can
            # not find it using clutter/pygtk
            # http://library.gnome.org/devel/pango/1.20
            # layout = self._obj.get_layout()
            # layout.set_height(self.inner_height)
            # Setting yalign also has no effect because there seems to be no
            # way to get the height used to draw the text.
            self._obj.set_clip(0, 0, self.inner_width, self.inner_height)
        if 'size' in self._sync_properties:
            self._obj.set_size(self.inner_width, self.inner_height)
            self._obj.set_clip(0, 0, self.inner_width, self.inner_height)
        self._obj.set_line_wrap(True)
        self._obj.set_line_wrap_mode(pango.WRAP_WORD_CHAR)
        self._obj.set_use_markup(True)
        self._obj.set_font_name("%s %spx" % (self.__font.name, self.__font.size))
        self._obj.set_color(backend.Color(*self.__color))
        self._obj.set_text(self.__text_eval)

    def _candy_sync_layout(self):
        """
        Layout the widget
        """
        super(Text, self)._candy_sync_layout()
        if self.xalign == Widget.ALIGN_LEFT:
            self._obj.set_alignment(Text.ALIGN_LEFT)
        if self.xalign == Widget.ALIGN_CENTER:
            self._obj.set_alignment(Text.ALIGN_CENTER)
        if self.xalign == Widget.ALIGN_RIGHT:
            self._obj.set_alignment(Text.ALIGN_RIGHT)

    @classmethod
    def candyxml_parse(cls, element):
        """
        Parse the XML element for parameter to create the widget.
        """
        return super(Text, cls).candyxml_parse(element).update(
            text=element.content, align=element.align, color=element.color,
            font=element.font)


# register widget to candyxml
Text.candyxml_register()
