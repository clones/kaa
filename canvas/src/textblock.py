__all__ = [ 'TextBlock' ]

from object import *
import libxml2, re

class TextBlock(Object):

    def __init__(self, markup = None):
        super(TextBlock, self).__init__()

        for prop in ("size", "pos", "clip"):
            self._supported_sync_properties.remove(prop)
        self._supported_sync_properties += [ "markup", "size", "pos", "clip" ]
    
        self._template_vars = {}
        self._processed_markup = None

        # Default size will grow to fill its container.
        #self["size"] = ("100%", "100%")
        if markup != None:
            self.set_markup(markup)

    def __str__(self):
        clsname = self.__class__.__name__
        markup = self["markup"]
        if len(markup) > 30:
            markup = markup[:30] + "..."
        return "<canvas.%s markup=\"%s\">" % (clsname, markup)

    def _canvased(self, canvas):
        super(TextBlock, self)._canvased(canvas)

        if not self._o and canvas.get_evas():
            o = canvas.get_evas().object_textblock_add()
            # FIXME: hardcoded defaults
            o.style_set("DEFAULT='font=arial font_size=16 align=left color=#ffffffff wrap=word' br='\n'")
            self._wrap(o)


    def _get_actual_size(self, child_asking = None):
        return self._o.geometry_get()[1]


    def _sync_property_markup(self):
        def replace_variables(match):
            key = match.group(1)
            if key in self._template_vars:
                return self._template_vars[key]
            return "@%s@" % key
        markup = re.sub("@(\w+)@", replace_variables, self._processed_markup)
        self._o.markup_set(markup)


    def _sync_property_clip(self):
        return True

    def _get_minimum_size(self):
        size = self._get_actual_size()
        return self._o.size_formatted_get()

    def _compute_size(self, size, child_asking, extents = None):
        if "auto" in size:
            size = list(size)
            formatted_size = self._o.size_formatted_get()
            for i in range(2):
                if size[i] == "auto":
                    size[i] = formatted_size[i]

        return super(TextBlock, self)._compute_size(size, child_asking, extents)

    def _parse_markup_xml(self, markup):
        doc = libxml2.parseMemory(markup, len(markup))
        lines = self._process_markup_node(doc, {"color": "#fff"})
        markup = "".join(lines)
        return re.sub("\s+|\n", " ", markup)

    def _process_markup_node(self, node, vars = {}):
        child = node.children
        text = []
        while child:
            end_tag = None
            if child.isText() and not child.children:
                text.append(child.content)
            elif child.name == "br":
                text.append("<br>")
            elif child.name == "format":
                text.append("<")
                for prop in ("color", "font", "style", "font_size", "shadow_color", "outline_color",
                             "align", "valign"):
                    if child.hasProp(prop):
                        vars[prop] = child.prop(prop)
                        text.append("%s=%s" % (prop, vars[prop]))

                text.append(">")
                end_tag = "</>"
            elif child.name == "u":
                text.append("<underline=on underline_color=%s>" % vars["color"])
                end_tag = "</>"
            elif child.name == "center":
                text.append("<align=center>")
                end_tag = "</>"
                

            if child.children:
                text.extend(self._process_markup_node(child, vars))
            if end_tag:
                text.append(end_tag)
            child = child.next

        return text

    def _set_property_markup(self, markup):
        self._processed_markup = self._parse_markup_xml("<style>%s</style>" % markup)
        self._set_property_generic("markup", markup)

    #
    # Public API
    #

    def set_markup(self, markup):
        self["markup"] = markup

    def get_markup(self):
        return self["markup"]

    def set_template_variable(self, **kwargs):
        self._template_vars.update(kwargs)
        self._force_sync_property("markup")
