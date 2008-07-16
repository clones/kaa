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
import clutter
import pango

# kaa.candy imports
import core


class Text(core.Widget, clutter.Label):
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

    def __init__(self, pos, size, text, font, color, align, context=None):
        clutter.Label.__init__(self)
        core.Widget.__init__(self, pos, size, context)
        text = self._regexp_space.sub(' ', text)
        if context:
            def eval_expression(matchobj):
                if self.eval_context(matchobj.groups()[0]):
                    return matchobj.groups()[1]
                return ''
            def replace_context(matchobj):
                # FIXME: maybe the string has markup to use
                return self.eval_context(matchobj.groups()[0]).replace('&', '&amp;').\
                       replace('<', '&lt;').replace('>', '&gt;')
            text = self._regexp_if.sub(eval_expression, text)
            text = self._regexp_eval.sub(replace_context, text).strip()
        text = self._regexp_br.sub('\n', text)
        layout = self.get_layout()
        self.set_line_wrap(True)
        self.set_line_wrap_mode(pango.WRAP_WORD_CHAR)
        self.set_use_markup(True)
        # requires pango 1.20
        # self.get_layout().set_height(70)
        if align == 'center':
            self.set_alignment(Text.ALIGN_CENTER)
        self.set_font_name("%s %spx" % (font.name, font.size))
        self.set_color(color)
        self.set_text(text)

    def set_color(self, color):
        super(Text, self).set_color(clutter.Color(*color))

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
