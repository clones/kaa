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
        self._properties = {}
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
        self._properties_serial += 1

    def _set_property_generic(self, key, value):
        self._properties[key] = value
        self._queue_render()

    def __delitem__(self, key):
        if key in self._properties:
            del self._properties[key]

    def _wrap(self, evas_object):
        self._o = evas_object
        if not self._o:
            return

        self._o._canvas_object = weakref(self)
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
            pos = map(lambda x,y: x+y, pos, parent["pos"])
            layer += parent["layer"]
            visible = visible and parent["visible"]
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
        if not isinstance(self._o, evas.Object):
            return

        props = self._get_relative_values()
        cur_pos, cur_size = self._o.geometry_get()

        if props["pos"] != cur_pos:
            self._o.move(props["pos"])
        if props["visible"] != self._o.visible_get():
            self._o.visible_set(props["visible"])
        if props["layer"] != self._o.layer_get():
            self._o.layer_set(props["layer"])
        if props["color"] != self._o.color_get():
            self._o.color_set(*props["color"])
        if self["size"] != (-1, -1) and self["size"] != cur_size:
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
        for child in self._children:
            child._uncanvased()

    def __setitem__(self, key, value):
        super(CanvasContainer, self).__setitem__(key, value)
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

    def add_container(self, pos = (0, 0), visible = True, color = (255, 255, 255, 255), layer = 0, name = None):
        c = CanvasContainer()
        c.move(pos)
        c.set_layer(layer)
        c.set_color(*color)
        c.set_visible(visible)
        c.set_name(name)
        self.add_child(c)
        return c

    def add_image(self, image, dst_pos = (0, 0), dst_size = (-1, -1),
                  src_pos = (0, 0), src_size = (-1, -1), visible = True,
                  color = (255, 255, 255, 255), layer = 0, name = None):
        img = CanvasImage(image)
        img.move(dst_pos)
        img.resize(dst_size)
        # Do src_pos/size via crop
        img.set_layer(layer)
        img.set_color(*color)
        img.set_visible(visible)
        img.set_name(name)
        self.add_child(img)
        return img




class CanvasImage(CanvasObject):

    def __init__(self, image_or_file = None):
        super(CanvasImage, self).__init__()
        self["loaded"] = False
        self["has_alpha"] = True
        if image_or_file:
            self.set_image(image_or_file)


    def set_image(self, image_or_file):
        del self["filename"], self["image"]
        if type(image_or_file) in types.StringTypes:
            self["filename"] = image_or_file
        elif imlib2 and type(image_or_file) == imlib2.Image:
            self["image"] = image_or_file
            self["image"].signals["changed"].connect_weak(self.set_dirty)
        else:
            raise ValueError, "Unsupported argument to set_image: " + repr(type(image_or_file))

        self["loaded"] = False


    def _canvased(self, canvas):
        super(CanvasImage, self)._canvased(canvas)

        if self._o:
            o = self._o
        else:
            o = canvas.get_evas().object_image_add()

        o.alpha_set(True)
        self._wrap(o)


    def _set_property_filename(self, filename):
        if self._o:
            self._o.load(filename)
        self._set_property_generic("filename", filename)


    def _set_property_image(self, image):
        assert(imlib2 and type(image) == imlib2.Image)
        self._set_property_generic("image", image)


    def _sync_properties(self):
        super(CanvasImage, self)._sync_properties()

        if not self["loaded"]:
            if "image" in self:
                size = self["image"].size
                print "Importing imlib2 image"
                self._o.size_set(size)
                self._o.resize(size)
                self._o.fill_set((0, 0), size)
                self._o.data_set(self["image"].get_raw_data(), copy = False)
            elif "filename" in self:
                self._o.load(self["filename"])

            self["loaded"] = True

        if self["size"] != (-1, -1) and ((0,0), self.get_size()) != self._o.fill_get():
            print "SET FILL"
            self._o.fill_set((0, 0), self.get_size())

        if self["has_alpha"] and self._o.alpha_get() != self["has_alpha"]:
            self._o.alpha_set(self["has_alpha"])

        if self["dirty"]:
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


    def as_image(self):
        if not imlib2:
            assert CanvasError, "kaa.imlib2 not available."

        if not self["image"]:
            # No existing Imlib2 image, so we need to make one.
            if self["loaded"]:
                # The evas object already exists, so create an Imlib2 image
                # from evas data and use the Imlib2 image as the buffer for
                # thee evas object.
                size = self._o.size_get()
                self["image"] = imlib2.new(size, self._o.data_get())
                self._o.data_set(self["image"].get_raw_data(), copy = False)
                print "MAKING IMAGE FROM EVAS OBJECT"

            elif self["filename"]:
                # Evas object not created yet, 
                self["image"] = imlib2.open(self["filename"])
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

    def _register_object_name(self, name, object):
        self._names[name] = weakref(object)

    def _unregister_object_name(self, name):
        if name in self._names:
            del self._names[name]

    def find_object_by_name(self, name):
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


    def _sync_properties(self):
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
        self._o.render()
        if vis == True:
            self._window.show()

        self._visibility_on_next_render = None

