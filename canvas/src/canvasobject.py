#__all__ = [ 'CanvasError', 'CanvasObject' ]

# XXX: all this stuff is in a single file right now since it's easier for
# initial development.  I'll split it up later.
__all__ = [ 'CanvasObject', 'CanvasError', 'CanvasContainer', 'CanvasImage', 
            'Canvas', 'X11Canvas' ]

import types
import kaa
from kaa import evas, display, notifier
from kaa.base import weakref
from kaa.notifier import Signal
try:
    from kaa import imlib2
except ImportError:
    imlib2 = None


class CanvasError(Exception):
    pass


class CanvasObject(object):

    def __init__(self):
        self._supported_properties = ["pos", "visible", "layer", "color", "size"]
        self._properties = {}
        self._changed_since_sync = {}
        self._properties_serial = 0
        self._relative_values_cache = { "serial": -1 }
        self._o = self._canvas = self._parent = None

        self["pos"] = (0, 0)
        self["size"] = (-1, -1)
        self["color"] = (255, 255, 255, 255)
        self["visible"] = True
        self["layer"] = 0



    def __contains__(self, key):
        return key in self._properties


    def __getitem__(self, key):
        if hasattr(self, "_get_property_" + key):
            return getattr(self, "_get_property_" + key)()
        if key in self._properties:
            return self._properties[key]
        return None

    def __setitem__(self, key, value):
        #print "Set property '%s', oldval=%s  newval=%s" % (key, repr(self[key]), repr(value))
        if self[key] == value:
            return False
        if hasattr(self, "_set_property_" + key):
            getattr(self, "_set_property_" + key)(value)
        else:
            self._set_property_generic(key, value)
        self._inc_properties_serial()

    def _inc_properties_serial(self):
        self._properties_serial += 1

    def _set_property_generic(self, key, value):
        self._properties[key] = value
        if self._changed_since_sync != None:
            self._changed_since_sync[key] = True
            if self._o:
                self._sync_properties()
        self._queue_render()

    def __delitem__(self, key):
        if key in self._properties:
            del self._properties[key]

    def _wrap(self, evas_object):
        self._o = evas_object
        if not self._o:
            return

        self._o._canvas_object = weakref(self)
        self._sync_properties()
        self._queue_render()


    def _queue_render(self):
        if self._canvas:
            self._canvas._queue_render(self)

    def _adopted(self, parent):
        self._parent = weakref(parent)

    def _orphaned(self):
        self._parent = None

    def _canvased(self, canvas):
        self._canvas = weakref(canvas)
        if self["name"]:
            self._canvas._register_object_name(self["name"], self)

    def _uncanvased(self):
        if self["name"] and self._canvas:
            self._canvas._unregister_object_name(self["name"])
        self._wrap(None)
        self._canvas = None


    def _get_relative_values(self, container = None, pos = None, layer = None, color = None, visible = None):
        if self._properties_serial <= self._relative_values_cache["serial"]:
            return self._relative_values_cache

        pos = (pos, self["pos"])[pos == None]
        layer = (layer, self["layer"])[layer == None]
        color = (color, self["color"])[color == None]
        visible = (visible, self["visible"])[visible == None]

        def _blend_pixel(a, b):
            tmp = (a * b) + 0x80
            return (tmp + (tmp >> 8)) >> 8

        parent = self._parent
        while parent:
            # We're not interested in most properties of the canvas itself,
            # because it usually maps to a physical window.  For example,
            # the window may be positioned at (50, 50) on the screen, so
            # we obviously don't want all objects on the canvas relative to
            # that ...
            if parent != self._canvas:
                pos = map(lambda x,y: x+y, pos, parent["pos"])
                visible = visible and parent["visible"]
                layer += parent["layer"]

            # ... except for color, which is a special case.
            color = map(_blend_pixel, color, parent["color"])

            if container and parent == container:
                break

            parent = parent._parent

        r = { "pos": pos, "layer": layer, "color": color, "visible": visible, "serial": self._properties_serial }
        self._relative_values_cache = r
        #print "Relative", self, r
        return r
            

    def _set_property_color(self, color):
        # If color element is None, use the existing value.
        if None in color:
            color = tuple(map(lambda x, y: (x,y)[x==None], color, self["color"]))
        r,g,b,a = color
        assert(type(r) == type(g) == type(b) == type(a) == int)
        if color != self["color"]:
            self._set_property_generic("color", color)
        return True


    def _sync_properties(self):
        if len(self._changed_since_sync) == 0:
            return False

        changed = self._changed_since_sync
        # Prevents reentry.
        self._changed_since_sync = None

        #print "SYNC PROPERTIES", self, changed

        for prop in self._supported_properties:
            if prop not in changed:
                continue
            getattr(self, "_sync_property_" + prop)()
            del changed[prop]

        self._changed_since_sync = changed
        return True


    def _sync_property_pos(self):
        self._o.move(self._get_relative_values()["pos"])

    def _sync_property_visible(self):
        self._o.visible_set(self._get_relative_values()["visible"])
    
    def _sync_property_layer(self):
        self._o.layer_set(self._get_relative_values()["layer"])

    def _sync_property_color(self):
        self._o.color_set(*self._get_relative_values()["color"])

    def _sync_property_size(self):
        if self["size"] == (-1, -1):
            return

        self._o.resize(self._get_computed_size(self["size"]))

    def _get_computed_size(self, (w, h)):
        orig_w, orig_h = self.get_size()
        aspect = orig_w / float(orig_h)

        if w == -1:
            w = h * aspect
        elif h == -1:
            h = w / aspect

        return int(w), int(h)



    # Public API

    def get_parent(self):
        return self._parent

    def move(self, (x, y)):
        assert(type(x) == int and type(y) == int)
        self["pos"] = (x, y)

    def set_color(self, r = None, g = None, b = None, a = None):
        self["color"] = (r, g, b, a)

    def show(self):
        self.set_visible(True)

    def hide(self):
        self.set_visible(False)

    def set_visible(self, visible):
        self["visible"] = visible

    def set_layer(self, layer):
        self["layer"] = layer

    def resize(self, size):
        self["size"] = size


    def get_size(self):
        if isinstance(self._o, evas.Object):
            return self._o.geometry_get()[1]
        return self["size"]

    def get_name(self):
        return self["name"]

    def set_name(self, name):
        self["name"] = name
        if self._canvas:
            self._canvas._register_object_name(name, self)


class CanvasContainer(CanvasObject):

    def __init__(self):
        self._children = []
        super(CanvasContainer, self).__init__()

    def _canvased(self, canvas):
        super(CanvasContainer, self)._canvased(canvas)
        for child in self._children:
            child._canvased(canvas)

    def _uncanvased(self):
        super(CanvasContainer, self)._uncanvased()
        for child in self._children:
            child._uncanvased()

    def _inc_properties_serial(self):
        super(CanvasContainer, self)._inc_properties_serial()
        for child in self._children:
            child._properties_serial += 1
   

    def _sync_properties(self):
        for child in self._children:
            child._sync_properties()

    def add_child(self, child):
        if child._parent:
            raise CanvasError, "Attempt to parent an adopted child."

        self._children.append(child)
        child._adopted(self)
        if isinstance(self, Canvas):
            child._canvased(self)
        elif self._canvas:
            child._canvased(self._canvas)

        return child

    def remove_child(self, child):
        if child not in self._children:
            return False
        self._children.remove(child)
        if child._o:
            child._o.hide()
        # FIXME: shouldn't access _queued_children directly
        if child._canvas and child in child._canvas._queued_children:
            del child._canvas._queued_children[child]
        child._orphaned()
        return True

    # Convenience functions for object creation.

    def _add_common(self, o, kwargs):
        if "pos" in kwargs:     o.move(kwargs["pos"])
        if "visible" in kwargs: o.set_visible(kwargs["visible"])
        if "color" in kwargs:   o.set_color(*kwargs["color"])
        if "name" in kwargs:    o.set_name(kwargs["name"])
        if "layer" in kwargs:   o.set_layer(kwargs["layer"])
        self.add_child(o)
        return o


    def add_container(self, **kwargs):
        return self._add_common(CanvasContainer(), kwargs)

    def add_image(self, image, **kwargs):
        img = CanvasImage(image)
        if "dst_size" in kwargs:
            img.resize(kwargs["dst_size"])
        # TODO: Do src_pos/size via crop
        if "dst_pos" in kwargs: 
            kwargs["pos"] = kwargs["dst_pos"]
        return self._add_common(img, kwargs)

    def add_text(self, text = None, **kwargs):
        return self._add_common(CanvasText(text), kwargs)


class CanvasText(CanvasObject):

    def __init__(self, text = None, font = "arial", size = 24, color = None):
        super(CanvasText, self).__init__()

        self._supported_properties += [ "text", "font" ]

        self.set_font(font, size)
        if text != None:
            self.set_text(text)
        if color != None:
            self.set_color(color)

    def _canvased(self, canvas):
        super(CanvasText, self)._canvased(canvas)

        if self._o:
            o = self._o
        else:
            o = canvas.get_evas().object_text_add()

        self._wrap(o)


    def set_font(self, font, size):
        self["font"] = (font, size)


    def get_font(self):
        if isinstance(self._o, evas.Object):
            return self._o.font_get()
        return self["font"]


    def set_text(self, text, color = None):
        self["text"] = text
        if color:
            self.set_color(color)


    def get_text(self):
        if isinstance(self._o, evas.Object):
            return self._o.text_get()
        return self["text"]


    def _sync_property_font(self):
        self._o.font_set(*self["font"])

    def _sync_property_text(self):
        self._o.text_set(self["text"])




class CanvasImage(CanvasObject):

    PIXEL_FORMAT_NONE = 0
    PIXEL_FORMAT_ARGB32 = 1
    PIXEL_FORMAT_YUV420P_601 = 2

    def __init__(self, image_or_file = None):
        super(CanvasImage, self).__init__()

        self._supported_properties += ["image", "filename", "pixels", "dirty", "size", "has_alpha"]

        self._loaded = False
        self["has_alpha"] = True

        if image_or_file:
            self.set_image(image_or_file)


    def set_image(self, image_or_file):
        del self["filename"], self["image"], self["pixels"]
        if type(image_or_file) in types.StringTypes:
            self["filename"] = image_or_file
        elif imlib2 and type(image_or_file) == imlib2.Image:
            self["image"] = image_or_file
            # Use weakref connection because we already hold a ref to the
            # image: avoids cycle.
            self["image"].signals["changed"].connect_weak(self.set_dirty)
        else:
            raise ValueError, "Unsupported argument to set_image: " + repr(type(image_or_file))

        self._loaded = False


    def _canvased(self, canvas):
        super(CanvasImage, self)._canvased(canvas)

        if self._o:
            o = self._o
        else:
            o = canvas.get_evas().object_image_add()

        self._wrap(o)


    def _set_property_filename(self, filename):
        assert(type(filename) == str)
        self._set_property_generic("filename", filename)


    def _set_property_image(self, image):
        assert(imlib2 and type(image) == imlib2.Image)
        self._set_property_generic("image", image)


    def _sync_property_image(self):
        if self._loaded:
            return
        size = self["image"].size
        self._o.size_set(size)
        self._o.resize(size)
        self._o.fill_set((0, 0), size)
        self._o.data_set(self["image"].get_raw_data(), copy = False)
        self._loaded = True

    def _sync_property_filename(self):
        if self._loaded:
            return
        self._o.load(self["filename"])
        self._loaded = True

    def _sync_property_pixels(self):
        if self._loaded:
            return
        data, w, h, format = self["pixels"]
        self._o.size_set((w, h))
        self._o.resize((w,h))
        self._o.fill_set((0, 0), (w,h))
        self._o.pixels_import(data, w, h, format)
        self._o.pixels_dirty_set()
        self._loaded = True


    def _sync_property_size(self):
        super(CanvasImage, self)._sync_property_size()
        self._o.fill_set((0, 0), self.get_size())
    
    def _sync_property_has_alpha(self):
        self._o.alpha_set(self["has_alpha"])
    
    def _sync_property_dirty(self):
        if not self["dirty"]:
            return

        self._o.pixels_dirty_set()
        if self["image"]:
            # Even though we're sharing the memory between the evas image buffer
            # and the Imlib2 image's buffer, we need to call this function
            # for canvas backends where this data gets copied again (like GL
            # textures).
            self._o.data_set(self["image"].get_raw_data(), copy = False)
        self["dirty"] = False


    def set_dirty(self, dirty = True):
        self["dirty"] = dirty

    def import_pixels(self, data, w, h, format):
        del self["filename"], self["image"], self["pixels"]
        self["pixels"] = (data, w, h, format)
        self._loaded = False


    def as_image(self):
        if not imlib2:
            assert CanvasError, "kaa.imlib2 not available."

        if not self["image"]:
            # No existing Imlib2 image, so we need to make one.
            if self._loaded:
                # The evas object already exists, so create an Imlib2 image
                # from evas data and use the Imlib2 image as the buffer for
                # thee evas object.
                size = self._o.size_get()
                self["image"] = imlib2.new(size, self._o.data_get())
                self._o.data_set(self["image"].get_raw_data(), copy = False)

            elif self["filename"]:
                # Evas object not created yet, 
                self["image"] = imlib2.open(self["filename"])

            elif self["pixels"]:
                raise CanvasError, "Can't convert not-yet-imported pixels to image."

            self["image"].signals["changed"].connect_weak(self.set_dirty)

        return self["image"]


    def get_image_size(self):
        return self._o.size_get()


    def set_has_alpha(self, has_alpha = True):
        self["has_alpha"] = has_alpha

    


class Canvas(CanvasContainer):

    def __init__(self, size):

        self.signals = {
            "key_press_event": Signal()
        }

        self._queued_children = {}
        self._names = {}
        kaa.signals["idle"].connect_weak(self._check_render_queued)

        super(Canvas, self).__init__()

    def __getattr__(self, attr):
        if attr == "fontpath":
            return self.get_evas().fontpath
        return CanvasContainer.__getattr__(self, attr)

    def __setattr__(self, attr, value):
        if attr == "fontpath":
            self.get_evas().fontpath = value
        else:
            CanvasContainer.__setattr__(self, attr, value)

    def _register_object_name(self, name, object):
        # FIXME: handle cleanup
        self._names[name] = weakref(object)

    def _unregister_object_name(self, name):
        if name in self._names:
            del self._names[name]

    def find_object(self, name):
        if name in self._names:
            object = self._names[name]
            if object:
                return object._ref()
            # Dead weakref, remove it.
            del self._names[name]


    def _get_property_pos(self):
        return 0, 0


    def _queue_render(self, child = None):
        if not child:
            child = self
        self._queued_children[child] = 1


    def _check_render_queued(self):
        if len(self._queued_children) == 0:
            return

        print "Render requested"
        for child in self._queued_children.keys():
            child._sync_properties()

        self._queued_children = {}
        self.render()


    def render(self):
        self._check_render_queued()
        self._o.render()


    def get_evas(self):
        return self._o


class X11Canvas(Canvas):

    def __init__(self, size, use_gl = False, title = "Canvas"):
        self._window = display.EvasX11Window(use_gl, size = size, title = "Kaa Display Test")
        super(X11Canvas, self).__init__(size)
        self._wrap(self._window.get_evas())

        self._window.signals["key_press_event"].connect_weak(self.signals["key_press_event"].emit)
        self._window.set_cursor_hide_timeout(1)


    def _sync_property_visible(self):
        self._visibility_on_next_render = self["visible"]


    def _set_property_visible(self, vis):
        # Delay window hide/show until next render, because we want the
        # the render to happen before the window gets shown.
        self._visibility_on_next_render = vis
        self._queue_render()
        self._set_property_generic("visible", vis)


    def _set_property_pos(self, pos):
        self._window.move(pos)
        self._set_property_generic("pos", pos)


    def _set_property_size(self, size):
        self._window.resize(size)
        self._set_property_generic("size", size)


    def render(self):
        self._check_render_queued()
        vis = self._visibility_on_next_render
        if vis == False:
            self._window.hide()
        print "Render canvas right now"
        self._o.render()
        if vis == True:
            self._window.show()

        self._visibility_on_next_render = None

