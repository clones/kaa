__all__ = [ 'CanvasError', 'Object' ]

import types, re
import _weakref
from kaa import evas
from kaa.base import weakref

_percent_re = re.compile("([\d.]+%)")

class CanvasError(Exception):
    pass


class Object(object):

    def __init__(self):
        # Properties will be synchronized to canvas in order.  "pos" should
        # be listed after "size" since pos may depend on size.
        self._supported_sync_properties = ["name", "expand", "visible", "layer", "color", "size", "pos", "clip"]
        self._properties = {}
        self._changed_since_sync = {}
        self._values_cache = {}
        self._in_sync_properties = False

        self._o = self._canvas = self._parent = None
        self._clip_object = None

        self["pos"] = (0, 0)
        self["size"] = ("auto", "auto")
        self["color"] = (255, 255, 255, 255)
        self["visible"] = True
        self["layer"] = 0
        self["clip"] = None
        self["expand"] = False  # can be False/True, or a percentage.


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
        #self._notify_parent_property_changed(key)
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
            #if self.get_evas():
            #    self._sync_properties()
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
        #self._sync_properties()
        self._apply_parent_clip()
        self._queue_render()


    def _queue_render(self, child = None):
        if self._parent:
            self._parent._queue_render(self)


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

    def _get_extents(self):
        if not self._parent:
            return 0, 0
        # Ask our parent our extents.
        return self._parent._get_extents(child_asking = self)

    def _get_minimum_size(self):
        # Must be implemented by subclass.
        return 0, 0

    def _get_actual_size(self):
        if not self._o:
            return 0, 0
        return self._o.geometry_get()[1]

                       
    def _compute_size(self, size, child_asking, extents = None):
        size = list(size)
        for index in range(2):
            if type(size[index]) == int:
                continue

            if "%" in size[index]:
                if not extents:
                    extents = self._get_extents()
                def calc_percent(match):
                    p = int(match.group(1)[:-1]) / 100.0 * extents[index]
                    return str(int(p))
                size[index] = int(_percent_re.sub(calc_percent, size[index]))
            elif size[index] == "auto":
                size[index] = self._get_actual_size()[index]


        return tuple(size)


    def _get_computed_size(self, child_asking = None):
        """
        Returns our computed size.  If child is specified, it is our size that
        as far as the child is concerned.  (Used for containers.)
        """
        size = self._get_cached_value("size", child_asking)
        if size:
            return size

        if type(self["size"][0]) == type(self["size"][1]) == int:
            return self["size"]

        #print "[SIZE]:", self
        #print "    for child", child_asking
        #print "        Compute %s " % str(self["size"])
        size = self._compute_size(self["size"], child_asking)
        self._set_cached_value("size", child_asking, size)
        #print "        Size Result: %s" % str(size)
        return size


    def _compute_pos(self, pos, child_asking):
        pos = list(pos)
        computed_size = extents = None
        for index in range(2):
            if type(pos[index]) == int:
                continue

            if pos[index] in ("bottom", "right", "center"):
                if not extents:
                    extents = self._parent._get_computed_size(child_asking = self)
                    #print "        Container: %s" % str(extents), self, child_asking, self._parent
                if not computed_size:
                    computed_size = self._get_computed_size()
                    #print "        Computed size: %s" % str(computed_size)

            if "%" in pos[index]:
                if not extents:
                    extents = self._parent._get_computed_size(child_asking = self)
                def calc_percent(match):
                    p = int(match.group(1)[:-1]) / 100.0 * extents[index]
                    return str(int(p))
                pos[index] = int(_percent_re.sub(calc_percent, pos[index]))
            elif pos[index] in ("top", "left"):
                pos[index] = 0
            elif pos[index] in ("bottom", "right"):
                pos[index] = extents[index] - computed_size[index]
            elif pos[index] == "center":
                pos[index] = int((extents[index] - computed_size[index]) / 2.0)
            else:
                raise ValueError, "Unsupported position '%s'" % pos[index]

        return pos

    def _get_computed_pos(self, child_asking = None):
        pos = self._get_cached_value("computed_pos", child_asking)
        if pos:
            return pos

        if type(self["pos"][0]) == type(self["pos"][1]) == int:
            return self["pos"]

        #print "[POS]:", self
        #print "    for child", child_asking
        #print "        Compute %s" % str(self["pos"])
        pos = self._compute_pos(self["pos"], child_asking)
        #print "        Pos Result: %s" % str(pos)
        self._set_cached_value("computed_pos", child_asking, pos)
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
        #print "< DIRTY CACHED VALUE", self, prop
        if prop in self._values_cache:
            del self._values_cache[prop]


    def _set_cached_value(self, prop, child, value):
        if child:
            child = _weakref.ref(child)
        if prop not in self._values_cache:
            self._values_cache[prop] = {}
        self._values_cache[prop][child] = value
        



    def _get_relative_values(self, prop, child_asking = None):
        value = self._get_cached_value(prop, child_asking)
        if value:
            return value

        assert(prop in ("pos", "layer", "color", "visible"))

        if prop == "pos":
            v = self._get_computed_pos(child_asking)
        else:
            v = self[prop]

        def _blend_pixel(a, b):
            tmp = (a * b) + 0x80
            return (tmp + (tmp >> 8)) >> 8

        if self._parent:
            p = self._parent._get_relative_values(prop, child_asking = self)

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
                    v += p + 1

            if prop == "color":
            # ... except for color, which is a special case.
                v = map(_blend_pixel, v, p)


        self._set_cached_value(prop, child_asking, v)
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

    def _request_reflow(self, what_changed = None, old = None, new = None, child_asking = None):
        #print "[OBJECT REFLOW]", self, child_asking, what_changed, old, new
        if what_changed == "size":
            # TODO: only need to resync pos if pos depends on size.
            self._force_sync_property("pos")
            # Size changed, so cached value is dirty.
            self._dirty_cached_value("size")
        if self._parent:
            self._parent._request_reflow(what_changed, old, new, child_asking = self)


    def _can_sync_property(self, property):
        if property == "name":
            return True

        return self._o != None


    def _sync_properties(self, updated_properties = []):
        # Note: Container relies on this function, so don't abort if 
        # self._o == None.  This function will only get called when the
        # object belongs to a canvas (but not necessarily when the underlying
        # Evas canvas has been created, as in the case of BufferCanvas)
        # XXX: this function is a performance hotspot; needs some work.
        if len(self._changed_since_sync) == 0 or self._in_sync_properties:
            return False #True

        #print "SYNC PROPS", self, self._changed_since_sync
        needs_render = False
        #changed = self._changed_since_sync
        self._in_sync_properties = True
        # Prevents reentry.
        #self._changed_since_sync = {}
        for prop in self._supported_sync_properties:
            if prop not in self._changed_since_sync:# or (not pre_render and prop in ("pos", "size", "clip")):
                continue
            if self._can_sync_property(prop) != False and \
               getattr(self, "_sync_property_" + prop)() != False:
                needs_render = True
                del self._changed_since_sync[prop]
                updated_properties.append(prop)
                #del changed[prop]
                #if prop in self._changed_since_sync:
                #    del self._changed_since_sync[prop]

        if self._changed_since_sync:
            # There are still some properties that haven't been synced.
            # Requeue this object for rendering.
            #print "Queueing rendering because", self._changed_since_sync
            self._queue_render()
        self._in_sync_properties = False
        return needs_render


    def _sync_property_pos(self):
        abs_pos = self._get_relative_values("pos")
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
        # TODO: if s > size extents, add clip.
        old_size = self._o.geometry_get()[1]
        self._o.resize(s)
        if s != old_size:
            self._request_reflow("size", old_size, s)

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

    def _sync_property_expand(self):
        if self._parent:
            self._parent._request_expand(self)

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
        if prop == "pos":
            self._dirty_cached_value("computed_pos")
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

    def set_expand(self, expand):
        self["expand"] = expand

    def expand(self, expand):
        self.set_expand(expand)

    def get_expand(self):
        return self["expand"]

