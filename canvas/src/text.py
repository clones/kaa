__all__ = [ 'Text' ]

from object import *
import time
try:
    from kaa import imlib2
    # Construct a gradient (white to black) image used for fading
    # out text that has clip set.
    line = ""
    for b in range(255, 0, -7) + [0]:
        line += chr(b)*4
    _text_fadeout_mask = imlib2.new((len(line)/4, 100), line * 100)
    del line
except ImportError:
    imlib2 = None


class Text(Object):

    def __init__(self, text = None, font = None, size = None, color = None):
        super(Text, self).__init__()

        for prop in ("size", "pos", "clip"):
            self._supported_sync_properties.remove(prop)
        self._supported_sync_properties += [ "clip", "font", "text", "size", "pos" ]
    
        # Clip to parent by default.
        self["clip"] = "auto"
        self._font = self._img = None

        self.set_font(font, size)
        if text != None:
            self.set_text(text)
        if color != None:
            self.set_color(*color)

    def __repr__(self):
        clsname = self.__class__.__name__
        return "<canvas.%s text=\"%s\">" % (clsname, self["text"])

    def _canvased(self, canvas):
        super(Text, self)._canvased(canvas)

        if not self._o and canvas.get_evas():
            # Use Imlib2 to draw Text objects for now, since Evas doesn't
            # support gradients as clip objects, we use Imlib2 and draw_mask
            # to kluge that effect.
            if imlib2:
                o = canvas.get_evas().object_image_add()
            else:
                o = canvas.get_evas().object_text_add()
            self._wrap(o)


    def _render_text_to_image(self, force = True):
        if not self._font or self["text"] == None:
            return

        t0=time.time()
        metrics = self._font.get_text_size(self["text"])
        # Create image size based on horizontal advance and vertical height.
        w, h = metrics[2], metrics[1]

        draw_mask = False
        if self["clip"] == "auto":
            extents = self._get_extents()
            if self["size"] != ("auto", "auto"):
                computed_size = self._get_computed_size()
                if self["size"][0] != "auto":
                    extents[0] = min(extents[0], computed_size[0])
                if self["size"][1] != "auto":
                    extents[1] = min(extents[1], computed_size[1])

            if extents[0] < w:
                w = extents[0]
                draw_mask = True
            h = min(h, extents[1])

        if w <= 0 or h <= 0:
            return

        if self._img and (w, h) == self._img.size:
            if not force:
                return

            i = self._img
            i.clear()
            self._dirty_cached_value("size")
        else:
            i = imlib2.new((w, h))

        # Need to append " " to work around a bug in Imlib2 1.2.1.004 and 
        # earlier.
        padding = self._get_computed_padding()
        i.draw_text((padding[3], padding[1]), self["text"] + " ", (255,255,255,255), self._font)
        if draw_mask:
            for y in range(0, i.size[1], _text_fadeout_mask.size[1]):
                i.draw_mask(_text_fadeout_mask, (i.size[0] -  _text_fadeout_mask.size[0], y))

        self._o.size_set(i.size)
        self._o.data_set(i.get_raw_data(), copy = False)
        self._o.resize(i.size)
        self._o.fill_set((0, 0), i.size)
        self._o.alpha_set(True)
        self._o.pixels_dirty_set()
        self._img = i

        self._remove_sync_property("font")
        self._remove_sync_property("text")
        self._remove_sync_property("clip")
        #print "RENDER", self["font"], self["text"], metrics, i.size, time.time()-t0, self._get_extents(), self._get_intrinsic_size()
        

    def _get_computed_font_size(self):
        font_name, font_size = self["font"]
        if self["size"][1] == "auto":
            if isinstance(font_size, str):
                font_size = self._compute_relative_value(font_size, 24)
            if self._o.type_get() == "image":
                # Imlib2 seems to want font size in points, so we need to
                # compensate.  (FIXME: this calculation is probably wrong.)
                font_size *= 0.79
            return font_size

        if self._o.type_get() != "image":
            # Requires support from kaa.evas for Imaging stuff.
            raise ValueError, "NYI"

        target_height = self._get_computed_size()[1]
        font = imlib2.load_font(font_name, target_height * 0.5)
        metrics = font.get_text_size(self["text"])
        diff = target_height * 0.5 / metrics[1]

        font = imlib2.load_font(font_name, target_height * diff)
        #metrics = font.get_text_size(self["text"])

        return target_height * diff


    def _get_intrinsic_size(self, child_asking = None):
        if self._o.type_get() == "image":
            if not self._img and self._font and self["text"] != None:
                metrics = self._font.get_text_size(self["text"])
                return metrics[0] + 2, metrics[1]

            return self._o.geometry_get()[1]

        metrics = self._o.metrics_get()
        return metrics["horiz_advance"] - metrics["inset"], metrics["max_ascent"] + metrics["max_descent"]

    def _sync_property_font(self):
        old_size = self._o.geometry_get()[1]

        font_name = self["font"][0]
        font_size = self._get_computed_font_size()

        if self._o.type_get() == "image":
            self._font = imlib2.load_font(font_name, font_size)
            self._render_text_to_image()
        else:
            self._o.font_set((font_name, font_size))

        new_size = self._o.geometry_get()[1]
        if old_size != new_size:
            #print "[TEXT REFLOW]: font change", old_size, new_size
            self._request_reflow("size", old_size, new_size)


    def _sync_property_text(self):
        old_size = self._o.geometry_get()[1]
        if self._o.type_get() == "image":
            self._render_text_to_image()
        else:
            self._o.text_set(self["text"])
        new_size = self._o.geometry_get()[1]
        if old_size != new_size:
            #print "[TEXT REFLOW]: text change", old_size, new_size
            self._request_reflow("size", old_size, new_size)


    def _set_property_clip(self, clip):
        if clip not in ("auto", None):
            raise ValueError, "Text objects only support clip 'auto' or None"
        self._set_property_generic("clip", clip)


    def _sync_property_clip(self):
        # We do our own clipping, no need to create the clip object.
        old_size = self._o.geometry_get()[1]
        if self._o.type_get() == "image":
            self._render_text_to_image(force = False)
        new_size = self._o.geometry_get()[1]
        if old_size != new_size:
            self._request_reflow("size", old_size, new_size)

        return True


    def _sync_property_size(self):
        old_size = self._o.geometry_get()[1]
        if self._o.type_get() == "image":
            # Calculate new font size and rerender text.
            self._sync_property_font()
        new_size = self._o.geometry_get()[1]
        if old_size != new_size:
            self._request_reflow("size", old_size, new_size)


    def _compute_size(self, size, child_asking, extents = None):
        # Currently text cannot scale or clip; computed size is always 
        # intrinsic size, so force to auto.
        #size = ("auto", "auto")
        return super(Text, self)._compute_size(size, child_asking, extents)


    def _get_minimum_size(self):
        return self._get_intrinsic_size()


    #
    # Public API
    #

    def set_font(self, font = None, size = None):
        assert(font == None or isinstance(font, basestring))
        assert(size == None or isinstance(size, (str, int)))
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
        if self._o and self._o.type_get() == "text":
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
        elif metric == "inset":
            return self._o.inset_get()

    def get_metrics(self):
        self._assert_canvased()
        return self._o.metrics_get()
    
