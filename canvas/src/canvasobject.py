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
        self._supported_sync_properties = ["pos", "visible", "layer", "color", "size", "name", "clip"]
        self._properties = {}
        self._changed_since_sync = {}
        self._properties_serial = 0
        self._relative_values_cache = { "serial": -1 }

        self._o = self._canvas = self._parent = None
        self._clip_object = None

        self["pos"] = (0, 0)
        self["size"] = (-1, -1)
        self["color"] = (255, 255, 255, 255)
        self["visible"] = True
        self["layer"] = 0
        self["clip"] = None



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

        if key in ("pos", "visible", "color", "layer"):
            self._inc_properties_serial()

        if hasattr(self, "_set_property_" + key):
            getattr(self, "_set_property_" + key)(value)
        else:
            self._set_property_generic(key, value)


    def _inc_properties_serial(self):
        self._properties_serial += 1


    def _set_property_generic(self, key, value):
        self._properties[key] = value
        if self._changed_since_sync != None:
            self._changed_since_sync[key] = True
            if self.get_evas():
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
        self._apply_parent_clip()
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

        for prop in self._supported_sync_properties:
            if prop not in changed:
                continue
            getattr(self, "_sync_property_" + prop)()
            del changed[prop]

        self._changed_since_sync = changed
        return True


    def _sync_property_pos(self):
        abs_pos = self._get_relative_values()["pos"]
        if isinstance(self._o, evas.Object):
            self._o.move(abs_pos)
        if self._clip_object:
            clip_pos = map(lambda x,y: x+y, self["clip"][0], abs_pos)
            self._clip_object.move(clip_pos)

    def _sync_property_visible(self):
        if isinstance(self._o, evas.Object):
            self._o.visible_set(self._get_relative_values()["visible"])
    
    def _sync_property_layer(self):
        if isinstance(self._o, evas.Object):
            self._o.layer_set(self._get_relative_values()["layer"])

    def _sync_property_color(self):
        if isinstance(self._o, evas.Object):
            self._o.color_set(*self._get_relative_values()["color"])

    def _sync_property_size(self):
        if self["size"] == (-1, -1):
            return

        if isinstance(self._o, evas.Object):
            self._o.resize(self._get_computed_size(self["size"]))

    def _sync_property_name(self):
        self._canvas._register_object_name(self["name"], self)

    def _sync_property_clip(self):
        if self["clip"] == None:
            if self._clip_object:
                if isinstance(self._o, evas.Object):
                    self._o.clip_unset()
                self._clip_object = None
                self._apply_parent_clip()
            return

        if not self._clip_object:
            self._clip_object = self.get_evas().object_rectangle_add()
            self._clip_object.show()
            self._apply_parent_clip()
            if isinstance(self._o, evas.Object):
                self._o.clip_set(self._clip_object)

        clip_pos, clip_size = self["clip"]
        clip_pos = map(lambda x,y: x+y, clip_pos, self._get_relative_values()["pos"])

        self._clip_object.move(clip_pos)
        self._clip_object.resize(clip_size)


    def _apply_parent_clip(self):
        if not self._o and not self._clip_object:
            return

        parent = self._parent
        while parent:
            if parent._clip_object:
                if self._clip_object:
                    self._clip_object.clip_set(parent._clip_object)
                elif isinstance(self._o, evas.Object):
                    self._o.clip_set(parent._clip_object)
                break
            parent = parent._parent
        else:
            if self._clip_object: 
                self._clip_object.clip_unset()

    def _get_computed_size(self, (w, h)):
        orig_w, orig_h = self.get_size()
        aspect = orig_w / float(orig_h)

        if w == -1:
            w = h * aspect
        elif h == -1:
            h = w / aspect

        return int(w), int(h)


    def _reset(self):
        # TODO
        pass

    def _assert_canvased(self):
        if not self._o:
            raise CanvasError, "Object must be canvased to call this function."

    #
    # Public API
    #

    def get_parent(self):
        return self._parent

    def get_canvas(self):
        return self._canvas

    def get_evas(self):
        if self._canvas:
            return self._canvas.get_evas()

    def move(self, (x, y)):
        assert(type(x) == int and type(y) == int)
        self["pos"] = (x, y)

    def set_pos(self, pos):
        self.move(pos)

    def get_pos(self):
        return self["pos"]

    def set_color(self, r = None, g = None, b = None, a = None):
        self["color"] = (r, g, b, a)

    def get_color(self):
        return self["color"]

    def show(self):
        self.set_visible(True)

    def hide(self):
        self.set_visible(False)

    def set_visible(self, visible):
        self["visible"] = visible

    def get_visible(self):
        return self["visible"]

    def set_layer(self, layer):
        self["layer"] = layer

    def get_layer(self):
        return self["layer"]

    def resize(self, size):
        self["size"] = size

    def set_size(self, size):
        self.resize(size)

    def get_size(self):
        if isinstance(self._o, evas.Object):
            return self._o.geometry_get()[1]
        return self["size"]

    def clip(self, pos = (0, 0), size = (-1, -1)):
        assert( -1 not in size )
        self["clip"] = (pos, size)

    def unclip(self):
        self["clip"] = None


    def get_name(self):
        return self["name"]

    def set_name(self, name):
        self["name"] = name


class CanvasContainer(CanvasObject):

    def __init__(self):
        self._children = []
        super(CanvasContainer, self).__init__()

        self._supported_sync_properties = ["clip", "name", "pos"]


    def _canvased(self, canvas):
        super(CanvasContainer, self)._canvased(canvas)
        for child in self._children:
            child._canvased(canvas)


    def _uncanvased(self):
        super(CanvasContainer, self)._uncanvased()
        for child in self._children:
            child._uncanvased()


    def _set_property_generic(self, key, value):
        super(CanvasContainer, self)._set_property_generic(key, value)

        if key not in ("name",):
            self._queue_children_sync_property(key)


    def _queue_children_sync_property(self, prop):
        for child in self._children:
            if type(child) == CanvasContainer:
                child._queue_children_sync_property(prop)
            else:
                child._changed_since_sync[prop] = True


    def _inc_properties_serial(self):
        super(CanvasContainer, self)._inc_properties_serial()
        for child in self._children:
            child._properties_serial += 1
   

    def _sync_properties(self):
        super(CanvasContainer, self)._sync_properties()
        for child in self._children:
            child._sync_properties()

    def _sync_property_clip(self):
        super(CanvasContainer, self)._sync_property_clip()
        self._apply_clip_to_children()


    def _apply_clip_to_children(self):
        for child in self._children:
            if type(child) == CanvasContainer:
                child._apply_clip_to_children()
            else:
                child._apply_parent_clip()

    def _set_property_size(self, size):
        if size != (-1, -1):
            raise CanvasError, "NYI: Can't set size for containers yet."


    #
    # Public API
    #

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
        self.add_child(o)
        if "pos" in kwargs:     o.move(kwargs["pos"])
        if "visible" in kwargs: o.set_visible(kwargs["visible"])
        if "color" in kwargs:   o.set_color(*kwargs["color"])
        if "name" in kwargs:    o.set_name(kwargs["name"])
        if "layer" in kwargs:   o.set_layer(kwargs["layer"])
        if "clip" in kwargs:    o.clip(*kwargs["clip"])
        if "size" in kwargs:    o.resize(kwargs["size"])
        return o


    def add_container(self, **kwargs):
        return self._add_common(CanvasContainer(), kwargs)

    def add_image(self, image, **kwargs):
        return self._add_common(CanvasImage(image), kwargs)

    def add_text(self, text = None, **kwargs):
        return self._add_common(CanvasText(text), kwargs)

    def add_rectangle(self, **kwargs):
        return self._add_common(CanvasRectangle(), kwargs)


class CanvasText(CanvasObject):

    def __init__(self, text = None, font = "arial", size = 24, color = None):
        super(CanvasText, self).__init__()

        self._supported_sync_properties += [ "text", "font" ]

        self.set_font(font, size)
        if text != None:
            self.set_text(text)
        if color != None:
            self.set_color(*color)

    def _canvased(self, canvas):
        super(CanvasText, self)._canvased(canvas)

        if not self._o:
            o = canvas.get_evas().object_text_add()
            self._wrap(o)


    def _sync_property_font(self):
        self._o.font_set(*self["font"])

    def _sync_property_text(self):
        self._o.text_set(self["text"])


    #
    # Public API
    #

    def set_font(self, font, size):
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
    



class CanvasImage(CanvasObject):

    PIXEL_FORMAT_NONE = 0
    PIXEL_FORMAT_ARGB32 = 1
    PIXEL_FORMAT_YUV420P_601 = 2

    def __init__(self, image_or_file = None):
        super(CanvasImage, self).__init__()

        self._supported_sync_properties += ["image", "filename", "pixels", "dirty", "size", "has_alpha"]

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

        if not self._o:
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


    #
    # Public API
    #

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
        if self["image"]:
            return self["image"].size
        self._assert_canvased()
        return self._o.size_get()


    def set_has_alpha(self, has_alpha = True):
        self["has_alpha"] = has_alpha

 
 
class CanvasRectangle(CanvasObject):

    def __init__(self, size = None, color = None):
        super(CanvasRectangle, self).__init__()

        if size:
            self.resize(size)
        if color:
            self.set_color(*color)
   
    def _canvased(self, canvas):
        super(CanvasRectangle, self)._canvased(canvas)
        if not self._o:
            o = canvas.get_evas().object_rectangle_add()
            self._wrap(o)


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


    #
    # Public API
    #

    def render(self):
        self._check_render_queued()
        self._o.render()


    def get_evas(self):
        return self._o


    def find_object(self, name):
        if name in self._names:
            object = self._names[name]
            if object:
                return object._ref()
            # Dead weakref, remove it.
            del self._names[name]

    def clip(self, pos = (0,0), size = (-1,-1)):
        raise CanvasError, "Can't clip whole canvases yet -- looks like a bug in evas."



class X11Canvas(Canvas):

    def __init__(self, size, use_gl = False, title = "Canvas"):
        self._window = display.EvasX11Window(use_gl, size = size, title = "Kaa Display Test")
        super(X11Canvas, self).__init__(size)
        self._wrap(self._window.get_evas())

        self._window.signals["key_press_event"].connect_weak(self.signals["key_press_event"].emit)
        self._window.set_cursor_hide_timeout(1)


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
