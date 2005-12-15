__all__ = [ 'Text' ]

from object import *

class Text(Object):

    def __init__(self, text = None, font = None, size = None, color = None):
        super(Text, self).__init__()

        for prop in ("size", "pos", "clip"):
            self._supported_sync_properties.remove(prop)
        self._supported_sync_properties += [ "text", "font", "size", "pos", "clip" ]

        self.set_font(font, size)
        if text != None:
            self.set_text(text)
        if color != None:
            self.set_color(*color)

    def __repr__(self):
        return "<canvas.Text object at 0x%x: \"%s\">" % (id(self), self["text"])

    def _canvased(self, canvas):
        super(Text, self)._canvased(canvas)

        if not self._o and canvas.get_evas():
            o = canvas.get_evas().object_text_add()
            self._wrap(o)


    def _sync_property_font(self):
        old_size = self._o.geometry_get()[1]
        self._o.font_set(*self["font"])
        if old_size != self._o.geometry_get()[1]:
            self._notify_parent_property_changed("size")

    def _sync_property_text(self):
        old_size = self._o.geometry_get()[1]
        self._o.text_set(self["text"])
        if old_size != self._o.geometry_get()[1]:
            self._notify_parent_property_changed("size")

    def _sync_property_size(self):
        # FIXME: if size specified for text, clip to size.
        return True

    #
    # Public API
    #

    def set_font(self, font = None, size = None):
        assert(font == None or isinstance(font, basestring))
        assert(size == None or type(size) == int)
        if self["font"]:
            cur_font, cur_size = self["font"]
        else:
            # FIXME: hardcoded defaults
            cur_font, cur_size = "arial", 24

        if not font:
            font = cur_font
        if size == None:
            size = cur_size

        self["font"] = (font, size)


    def get_font(self):
        if self._o:
            return self._o.font_get()
        return self["font"]


    def set_text(self, text, color = None):
        self["text"] = text
        if color:
            self.set_color(*color)


    def get_text(self):
        if self._o:
            return self._o.text_get()
        return self["text"]

    def get_metric(self, metric):
        self._assert_canvased()
        if metric == "ascent":
            return self._o.ascent_get()
        elif metric == "descent":
            return self._o.descent_get()
        elif metric == "max_ascent":
            return self._o.max_ascent_get()
        elif metric == "max_descent":
            return self._o.max_descent_get()
        elif metric == "horiz_advance":
            return self._o.horiz_advance_get()
        elif metric == "vert_advance":
            return self._o.vert_advance_get()
        elif metric == "insert":
            return self._o.inset_get()

    def get_metrics(self):
        self._assert_canvased()
        return self._o.metrics_get()
    
