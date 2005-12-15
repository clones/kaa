__all__ = [ 'CanvasError', 'Object' ]

import types, re
import _weakref
from kaa import evas
from kaa.base import weakref

class CanvasError(Exception):
    pass


class Object(object):

    def __init__(self):
        # Properties will be synchronized to canvas in order.  "pos" should
        # be listed after "size" since pos may depend on size.
        self._supported_sync_properties = ["name", "visible", "layer", "color", "size", "pos", "clip"]
        self._properties = {}
        self._changed_since_sync = {}
        self._values_cache = {}

        self._o = self._canvas = self._parent = None
        self._clip_object = None

        self["pos"] = (0, 0)
        self["size"] = ("auto", "auto")
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

        self._dirty_cached_value(key)
        if key == "pos":
            self._dirty_cached_value("computed_pos")
        self._notify_parent_property_changed(key)
        #if key in ("pos", "visible", "color", "layer", "size"):
        #    self._inc_properties_serial()

        if hasattr(self, "_set_property_" + key):
            getattr(self, "_set_property_" + key)(value)
        else:
            self._set_property_generic(key, value)


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
        self._clip_object = None
        if not self._o:
            return

        self._o._canvas_object = weakref(self)
        self._force_sync_all_properties()
        self._sync_properties()
        self._apply_parent_clip()
        self._queue_render()


    def _queue_render(self):
        if self._canvas:
            self._canvas._queue_render(self)

    def _adopted(self, parent):
        self._parent = weakref(parent)
        self._force_sync_all_properties()

    def _orphaned(self):
        self._parent = None

    def _canvased(self, canvas):
        if canvas == self._canvas:
            return

        self._canvas = weakref(canvas)
        if self["name"]:
            self._canvas._register_object_name(self["name"], self)


    def _uncanvased(self):
        if self["name"] and self._canvas:
            self._canvas._unregister_object_name(self["name"])
        self._wrap(None)
        self._canvas = None


    # Sizes: (expr, expr) where expr is: constant integer N, "N%", for images,
    #        if N is 0: orig value, -1: keep aspect
    # Pos: (expr, expr) where expr is constant integer N, "N%", variables:
    #      width, height, and valid python expr, e.g. 50%-(width/2) which
    #      means "center", also available: "top", "bottom"

    def _get_actual_size(self):
        return self._o.geometry_get()[1]

    def _compute_expr_re_cb_get_object_value(self, match):
        # FIXME: object A that depends on values from object B needs
        # to get reflowed if B changes.  Currently this still works
        # because when any object changes pos/size, the whole canvas
        # gets reflowed.  But eventually that will get fixed, and when
        # it does, this will need to get fixed.  (Will need to
        # maintain an object dependency tree.)
        name, value = match.group(1), match.group(2)
        o = self.get_canvas().find_object(name)
        if not o:
            raise ValueError, "Unknown object '%s' referenced in expression" % name
        if value == "width":
            return str(o.get_computed_size()[0])
        elif value == "height":
            return str(o.get_computed_size()[1])
        elif value == "left":
            return str(o.get_computed_pos()[0])
        elif value == "top":
            return str(o.get_computed_pos()[1])
        elif value == "right":
            return str(o.get_computed_pos()[0] + o.get_computed_size()[0])
        elif value == "bottom":
            return str(o.get_computed_pos()[1] + o.get_computed_size()[1])
        else:
            raise ValueError, "Unknown object value '%s' referenced in expression" % value
                       
    def _compute_size(self, parent_val, val):
        if not (type(parent_val[0]) == type(parent_val[1]) == int):
            raise CanvasError, "Invalid size for parent; ensure canvas has fixed size."
        val = list(val)
        for index in range(2):
            if type(val[index]) == int:
                continue

            if "%" in val[index]:
                def calc_percent(match):
                    p = int(match.group(1)[:-1]) / 100.0 * parent_val[index]
                    return str(int(p))
                val[index] = re.sub("([\d.]+%)", calc_percent, val[index])
            if "." in val[index]:
                val[index] = re.sub("(\w+)\.(\w+)", self._compute_expr_re_cb_get_object_value, val[index])
            if val[index] == "auto":
                val[index] = self._get_actual_size()[index]
                continue

            val[index] = eval(val[index], {}, {})

        return tuple(val)


    def _get_computed_size(self, child = None):
        """
        Returns the computed size of the object, or for the child object 
        if specified (used for Containers).
        """
        # TODO: this function gets called a LOT.  Cache this value.  This
        # value varies based on child paramter, so need to keep a dict that
        # maps child -> size.
        #print "Computing new size", self, self["size"]
        size = self._get_cached_value("size", child)
        if size:
            return size

        #print "XXX Computing size", self, child
        if self._parent:
            # Determine the size of our container (ask parent).
            psize = self._parent._get_computed_size(child = self)
            size = self._compute_size(psize, self["size"])
        else:
            size = self._compute_size(self["size"], self["size"])
        self._set_cached_value("size", child, size)
        return size


    def _compute_pos(self, pos, computed_size, parent_size):
        pos = list(pos)
        #print "Computing pos for", self, pos, computed_size, parent_size
        for index in range(2):
            if type(pos[index]) == int:
                continue

            locals = {
                "top": 0, 
                "left": 0, 
                "center": int((parent_size[index] - computed_size[index]) / 2.0),
                "right": parent_size[index] - computed_size[index], 
                "bottom": parent_size[index] - computed_size[index], 
                "width": computed_size[0],
                "height": computed_size[1] 
            }

            if "%" in pos[index]:
                def calc_percent(match):
                    p = int(match.group(1)[:-1]) / 100.0 * parent_size[index]
                    return str(int(p))
                pos[index] = re.sub("([\d.]+%)", calc_percent, pos[index])
            if "." in pos[index]:
                pos[index] = re.sub("(\w+)\.(\w+)", self._compute_expr_re_cb_get_object_value, pos[index])


            pos[index] = eval(pos[index], locals, {})

        return pos

    def _get_cached_value(self, prop, child):
        if child:
            child = _weakref.ref(child)

        if prop in self._values_cache:
            if child in self._values_cache[prop]:
                #print "CACHE HIT", self, prop, child, self._values_cache[prop][child]
                return self._values_cache[prop][child]

        #print "CACHE MISS", self, prop, child

    def _dirty_cached_value(self, prop):
        #self._values_cache = {}
        if prop in self._values_cache:
            del self._values_cache[prop]


    def _set_cached_value(self, prop, child, value):
        if child:
            child = _weakref.ref(child)
        if prop not in self._values_cache:
            self._values_cache[prop] = {}
        self._values_cache[prop][child] = value
        

    def _get_computed_pos(self, child = None):
        pos = self._get_cached_value("computed_pos", child)
        if pos:
            return pos

        #print "XXX Computing pos", self, child
        size = self._get_computed_size()
        if self._parent:
            parent_size = self._parent._get_computed_size(child = self)
        else:
            parent_size = None
        pos = self._compute_pos(self["pos"], size, parent_size)
        #print "_get_computed_pos NEW VALUE", self, " - size - ",self["size"], size, " - parent size - ", parent_size, " - calculated pos", pos
        self._set_cached_value("computed_pos", child, pos)
        #print "Returned computed pos", self, pos
        return pos


    def _get_relative_values(self, prop, child = None):
        value = self._get_cached_value(prop, child)
        if value:
            return value

        assert(prop in ("pos", "layer", "color", "visible"))

        if prop == "pos":
            v = self._get_computed_pos(child)
        else:
            v = self[prop]

        def _blend_pixel(a, b):
            tmp = (a * b) + 0x80
            return (tmp + (tmp >> 8)) >> 8

        if self._parent:
            p = self._parent._get_relative_values(prop, child = self)

            # We're not interested in most properties of the canvas itself,
            # because it usually maps to a physical window.  For example,
            # the window may be positioned at (50, 50) on the screen, so
            # we obviously don't want all objects on the canvas relative to
            # that ...
            if self._parent != self._canvas:
                if prop == "pos":
                    v = map(lambda x,y: x+y, v, p)
                elif prop == "visible":
                    v = v and p
                elif prop == "layer":
                    v += p

            if prop == "color":
            # ... except for color, which is a special case.
                v = map(_blend_pixel, v, p)


        self._set_cached_value(prop, child, v)
        return v
        
            

    def _set_property_color(self, color):
        # If color element is None, use the existing value.
        if None in color:
            color = tuple(map(lambda x, y: (x,y)[x==None], color, self["color"]))
        # Clamp color values to 0-255 range.
        color = [ max(0, min(255, c)) for c in color ]
        r,g,b,a = color
        assert(type(r) == type(g) == type(b) == type(a) == int)
        if color != self["color"]:
            self._set_property_generic("color", color)
        return True

    def _notify_parent_property_changed(self, prop):
        if self._parent:
            self._parent._child_property_changed(self, prop)

    def _can_sync_property(self, property):
        if property == "name":
            return True

        return self._o != None


    def _sync_properties(self, pre_render = False):
        # Note: Container relies on this function, so don't abort if 
        # self._o == None.  This function will only get called when the
        # object belongs to a canvas (but not necessarily when the underlying
        # Evas canvas has been created, as in the case of BufferCanvas)
        # XXX: this function is a performance hotspot; needs some work.
        if len(self._changed_since_sync) == 0:
            return True

        retval = False
        changed = self._changed_since_sync
        # Prevents reentry.
        self._changed_since_sync = {}
        #print "SYNC PROPS", self, changed
        for prop in self._supported_sync_properties:
            if prop not in changed or (not pre_render and prop in ("pos", "size", "clip")):
                continue
            if self._can_sync_property(prop) != False and \
               getattr(self, "_sync_property_" + prop)() != False:
                retval = True
                del changed[prop]
            #else:
            #    print "Sync failure:", prop, self, self._o, self._can_sync_property(prop)

        self._changed_since_sync.update(changed)
        if changed:
            # There are still some properties that haven't been synced.
            # Requeue this object for rendering.
            self._queue_render()
        return retval


    def _sync_property_pos(self):
        abs_pos = self._get_relative_values("pos")
        print "SYNC POS", self, abs_pos
        self._o.move(abs_pos)
        if self._clip_object:
            clip_pos = map(lambda x,y: x+y, self["clip"][0], abs_pos)
            self._clip_object.move(clip_pos)

    def _sync_property_visible(self):
        self._o.visible_set(self._get_relative_values("visible"))
    
    def _sync_property_layer(self):
        self._o.layer_set(self._get_relative_values("layer"))

    def _sync_property_color(self):
        self._o.color_set(*self._get_relative_values("color"))

    def _sync_property_size(self):
        s = self._get_computed_size()
        self._o.resize(s)

    def _sync_property_name(self):
        self._canvas._register_object_name(self["name"], self)

    def _sync_property_clip(self):
        if self["clip"] == None:
            if self._clip_object:
                if isinstance(sef._o, evas.Object):
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
        clip_pos = map(lambda x,y: x+y, clip_pos, self._get_relative_values("pos"))

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


    def _reset(self):
        self._o = self._clip_object = None
        self._force_sync_all_properties()

    def _force_sync_all_properties(self):
        for prop in self._supported_sync_properties:
            if prop in self:
                self._changed_since_sync[prop] = True
                self._dirty_cached_value(prop)
        self._queue_render()

    def _force_sync_property(self, prop):
        assert(prop in self._supported_sync_properties)
        self._dirty_cached_value(prop)
        if prop in self:
            self._changed_since_sync[prop] = True
        self._queue_render()


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
        assert(type(size) in (list, tuple) and len(size) == 2)
        self["size"] = size

    def set_size(self, size):
        assert(type(size) in (list, tuple) and len(size) == 2)
        self.resize(size)

    def get_size(self):
        return self["size"]

    def get_computed_size(self):
        return self._get_computed_size()

    def get_computed_pos(self):
        return self._get_computed_pos()

    def clip(self, pos = (0, 0), size = (-1, -1)):
        assert( -1 not in size )
        self["clip"] = (pos, size)

    def unclip(self):
        self["clip"] = None


    def get_name(self):
        return self["name"]

    def set_name(self, name):
        self["name"] = name

