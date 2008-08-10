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
import core


class Text(core.Widget):
    """
    Complex text widget.
    """
    candyxml_name = 'text'
    context_sensitive = True

    ALIGN_CENTER = pango.ALIGN_CENTER

    _regexp_space = re.compile('[\n\t \r][\n\t \r]+')
    _regexp_if = re.compile('#if(.*?):(.*?)#fi ?')
    _regexp_eval = re.compile('\$([a-zA-Z_\.\[\]]*)')
    _regexp_br = re.compile(' *<br/> *')

    __text = __text_eval = ''
    __color = None

    def __init__(self, pos, size, text, font, color, align, context=None):
        super(Text, self).__init__(pos, size, context)
        self.__align = align
        self.font = font
        self.text = text
        self.color = color

    @property
    def text(self):
        return self.__text

    @text.setter
    def text(self, text):
        self.__text = text
        def eval_expression(matchobj):
            if self.eval_context(matchobj.groups()[0]):
                return matchobj.groups()[1]
            return ''
        def replace_context(matchobj):
            # FIXME: maybe the string has markup to use
            return self.eval_context(matchobj.groups()[0]).replace('&', '&amp;').\
                   replace('<', '&lt;').replace('>', '&gt;')
        if self.get_context():
            # we have a context, use it
            text = self._regexp_space.sub(' ', text)
            text = self._regexp_if.sub(eval_expression, text)
            text = self._regexp_eval.sub(replace_context, text).strip()
        self.__text_eval = self._regexp_br.sub('\n', text)
        self._queue_sync(rendering=True)

    @property
    def color(self):
        return self.__color

    @color.setter
    def color(self, color):
        if not isinstance(color, Color):
            color = Color(color)
        self.__color = color

    @property
    def font(self):
        return self.__font

    @font.setter
    def font(self, font):
        if not isinstance(font, Font):
            font = Font(font)
        self.__font = font
        self._queue_sync(rendering=True)

    def _candy_render(self):
        """
        Render the widget
        """
        if not self._obj:
            self._obj = backend.Label()
            self._obj.show()
            self._obj.set_size(self.width, self.height)
        if 'size' in self._sync_properties:
            self._obj.set_size(self.width, self.height)
        layout = self._obj.get_layout()
        self._obj.set_line_wrap(True)
        self._obj.set_line_wrap_mode(pango.WRAP_WORD_CHAR)
        self._obj.set_use_markup(True)
        # requires pango 1.20
        # layout.set_height(70)
        if self.__align == 'center':
            self._obj.set_alignment(Text.ALIGN_CENTER)
        self._obj.set_font_name("%s %spx" % (self.__font.name, self.__font.size))
        self._obj.set_color(backend.Color(*self.__color))
        self._obj.set_text(self.__text_eval)

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
