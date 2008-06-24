# -*- coding: iso-8859-1 -*-
# -----------------------------------------------------------------------------
# text.py - Text Widget
# -----------------------------------------------------------------------------
# $Id$
#
# -----------------------------------------------------------------------------
# -----------------------------------------------------------------------------

# python imports
import re
import pango

# gui imports
import core
import kaa.candy

class Text(core.Text):
    """
    Complex text widget.
    """
    __gui_name__ = 'text'
    context_sensitive = True

    _regexp_space = re.compile('[\n\t \r][\n\t \r]+')
    _regexp_if = re.compile('#if(.*?):(.*?)#fi ?')
    _regexp_eval = re.compile('\$([a-zA-Z_\.\[\]]*)')
    _regexp_br = re.compile(' *<br/> *')

    def __init__(self, pos, size, text, font, color, align, context=None):
        super(Text, self).__init__(pos, size, context=context)
        text = self._regexp_space.sub(' ', text)
        if context:
            depends = []
            def eval_expression(matchobj):
                if not matchobj.groups()[0] in depends:
                    depends.append(matchobj.groups()[0])
                if eval(matchobj.groups()[0], context):
                    return matchobj.groups()[1]
                return ''
            def replace_context(matchobj):
                if not matchobj.groups()[0] in depends:
                    depends.append(matchobj.groups()[0])
                # FIXME: maybe the string has markup to use
                return eval(matchobj.groups()[0], context).replace('&', '&amp;').\
                       replace('<', '&lt;').replace('>', '&gt;')
            text = self._regexp_if.sub(eval_expression, text)
            text = self._regexp_eval.sub(replace_context, text).strip()
            self.set_dependency(*depends)
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

    @classmethod
    def parse_XML(cls, element):
        """
        Parse the XML element for parameter to create the widget.
        """
        return super(Text, cls).parse_XML(element).update(
            text=element.content, align=element.align, color=element.color,
            font=element.font)

# register widget to the core
kaa.candy.xmlparser.register(Text)
