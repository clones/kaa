__all__ = [ 'CanvasError', 'Object' ]

import types, re
import _weakref
from kaa import evas
from kaa.base import weakref
from kaa.notifier import Signal
import animation

_percent_re = re.compile("([\d.]+%)")

class CanvasError(Exception):
    pass


class Object(object):

    def __init__(self):
        self.signals = {
            "moved": Signal(),
            "resized": Signal(),
            "wrapped": Signal()
        }

        # Properties will be synchronized to canvas in order.  "pos" should
        # be listed after "size" since pos may depend on size.
        self._supported_sync_properties = [
            "name", "expand", "visible", "display", "layer", 
            "color", "size", "pos", "clip", "margin"
        ]
        self._properties = {}
        self._changed_since_sync = {}
        self._values_cache = {}
        self._in_sync_properties = False

        self._o = self._canvas = self._parent = None
        self._clip_object = None

        # Position tuple: left, top, right, bottom, hcenter, vcenter
        self["pos"] = (0, 0, None, None, None, None)
        self["size"] = ("auto", "auto")
        self["color"] = [255, 255, 255, 255]
        self["visible"] = True
        self["layer"] = 0
        self["clip"] = None
        self["expand"] = False  # can be False/True, or a percentage.
        self["display"] = True
        self["margin"] = (0, 0, 0, 0)


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

        self.signals["wrapped"].emit()


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


    def _get_extents(self):
        if not self._parent:
            return 0, 0
        # Ask our parent our extents.
        return self._parent._get_extents(child_asking = self)

    def _get_minimum_size(self):
        # Must be implemented by subclass.
        return 0, 0

    def _get_actual_size(self):
        return self._o.geometry_get()[1]

    def _get_fixed_pos(self):
        """
        Returns the top left coordinates of the object's position only if
        it is a fixed position, and not a relative position.  If the 
        coordinate is relative (i.e. dependent on the parent size), then None
        is returned.  Otherwise an integer is returned for that coordinate.
        """
        pos = [None, None]
        # TODO: handle fixed coords for right/bottom/[vh]center
        if type(self["pos"][0]) == int:
            pos[0] = self["pos"][0]
        if type(self["pos"][1]) == int:
            pos[1] = self["pos"][1]

        return pos

    def _get_fixed_size(self, resolve_auto = True):
        """
        Returns the width and height of the object only if they are fixed
        sizes, and not relative sizes.  If the dimension is relative (i.e.
        dependent on the parent size), then None is returned.  Otherwise an
        integer is returned for that dimension.  If the dimension is set to
        "auto" and resolve_auto is True, the actual value will be returned,
        otherwise "auto" will be returned.  (This is useful if the caller is
        only interested whether or not the object's size is fixed, not exactly
        what that fixed size is.)
        """
        size = [None, None]
        if "auto" in self["size"]:
            if resolve_auto:
                actual_size = self._get_actual_size()
            else:
                actual_size = ("auto", "auto")
        for i in range(2):
            if self["size"][i] == "auto":
                size[i] = actual_size[i]
            elif type(self["size"][i]) == int:
                size[i] = self["size"][i]

        return size

    def _is_size_calculated_from_pos(self):
        ret = [False, False]
        if self["pos"][0] != None and self["pos"][2] != None:
            ret[0] = True
        if self["pos"][1] != None and self["pos"][3] != None:
            ret[1] = True
        return ret

    def _compute_size(self, size, child_asking, extents = None):
        size = list(size)
        if True in self._is_size_calculated_from_pos():
            size_from_pos = self._compute_pos(self["pos"], child_asking)[1]
            if None not in size_from_pos:
                # Both dimensions computed from position, return right away.
                return size_from_pos

            # Substitute those dimensions that are computed from position in
            # size list and resume computation.
            if size_from_pos[0] != None:
                size[0] = size_from_pos[0]
            if size_from_pos[1] != None:
                size[1] = size_from_pos[1]


        for index in range(2):
            if type(size[index]) == int:
                continue

            if type(size[index]) == str and "%" in size[index]:
                if not extents:
                    extents = self._get_extents()
                size[index] = int(float(size[index].replace("%", "")) / 100.0 * extents[index])
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

        #print "[SIZE]:", self
        #print "    for child", child_asking
        #print "        Compute %s " % str(self["size"])
        size = self._compute_size(self["size"], child_asking)
        self._set_cached_value("size", child_asking, size)
        #print "        Size Result: %s" % str(size)
        return size


    def _compute_pos(self, pos, child_asking):
        computed_pos = [None, None]
        computed_size = [None, None]
        left, top, right, bottom, hcenter, vcenter = pos
        if None in pos[:2]:
            computed_size = self._get_computed_size()
            parent_size = self._parent._get_computed_size(child_asking = self)
        elif type(left) == str or type(top) == str or (left != None and right != None) or \
             (top != None and bottom != None):
            parent_size = self._parent._get_computed_size(child_asking = self)
        else:
            parent_size = [0, 0]  # dummy values

        def calc_value(value, total):
            if type(value) == int:
                return value
            def calc_percent(m):
                return str(int(int(m.group(2)) / 100.0 * total))
            value = re.sub("((\d+)%)", calc_percent, value)
            # TODO: rewrite not to use eval.
            return eval(value)
        
        if left != None and right != None:
            computed_pos[0] = calc_value(left, parent_size[0])
            r = calc_value(right, parent_size[0])
            computed_size[0] = r - computed_pos[0]
        elif left != None:
            computed_pos[0] = calc_value(left, parent_size[0])
        elif right != None:
            computed_pos[0] = calc_value(right, parent_size[0]) - computed_size[0]
        elif hcenter != None:
            computed_pos[0] = calc_value(hcenter, parent_size[0]) - computed_size[0] / 2
            
        if top != None and bottom != None:
            computed_pos[1] = calc_value(left, parent_size[1])
            b = calc_value(bottom, parent_size[1])
            computed_size[1] = b - computed_pos[1]
        elif top != None:
            computed_pos[1] = calc_value(top, parent_size[1])
        elif bottom != None:
            computed_pos[1] = calc_value(bottom, parent_size[1]) - computed_size[1]
        elif vcenter != None:
            computed_pos[1] = calc_value(vcenter, parent_size[1]) - computed_size[1] / 2

        #print "[CALC POS]", self, computed_size, parent_size, pos, computed_pos
        return computed_pos, computed_size


    def _get_computed_pos(self, child_asking = None):
        pos = self._get_cached_value("computed_pos", child_asking)
        if pos:
            return pos

        if type(self["pos"][0]) == type(self["pos"][1]) == int:
            return self["pos"][0:2]

        #print "[POS]:", self
        #print "    for child", child_asking
        #print "        Compute %s" % str(self["pos"])
        pos = self._compute_pos(self["pos"], child_asking)[0]
        #print "        Pos Result: %s" % str(pos)
        self._set_cached_value("computed_pos", child_asking, pos)
        return pos

    def _compute_clip(self, clip, child_asking):
        if clip == "auto":
            pos = 0, 0
            size = "100%", "100%"
        else:
            pos, size = clip

        def resolve(val, max):
            if type(val) == str:
                if val.replace("-", "").isdigit():
                    return int(val)
                elif "%" in val:
                    return int(float(val.replace("%", "")) / 100.0 * max)
                    
            return val

        computed_size = self._get_computed_size()
        pos = [ resolve(x,max) for x,max in zip(pos, computed_size) ]
        size = [ resolve(x,max) for x,max in zip(size, computed_size) ]

        for i in range(2):
            if size[i] <= 0:
                size[i] = computed_size[i] + size[i]

        return pos, size


    def _get_computed_clip(self, child_asking = None):
        # TODO: cache
        clip = self._compute_clip(self["clip"], child_asking)
        return clip


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
            v = list(self._get_computed_pos(child_asking))
            v[0] += self["margin"][0]
            v[1] += self["margin"][1]
        elif prop == "visible":
            v = self["visible"] and self["display"]
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
                    v += p# + 1

            if prop == "color":
            # ... except for color, which is a special case.
                v = map(_blend_pixel, v, p)


        self._set_cached_value(prop, child_asking, v)
        return v

    def _parse_color(self, color):
        """
        Parse a color that is either a 3- or 4-tuple of integers, or an
        html-style spec like #rrggbb or #rrggbbaa.
        """
        if isinstance(color, basestring):
            assert(color[0] == "#" and len(color) in (7, 9))
            r = int(color[1:3], 16)
            g = int(color[3:5], 16)
            b = int(color[5:7], 16)
            if len(color) > 7:
                a = int(color[7:9], 16)
            else:
                a = self["color"][3]
            color = r, g, b, a
        elif type(color) in (list, tuple):
            # If color element is None, use the existing value.
            if None in color:
                color = tuple(map(lambda x, y: (x,y)[x==None], color, self["color"]))

            # Clamp color values to 0-255 range.
            color = [ max(0, min(255, c)) for c in color ]
            r,g,b,a = color
            assert(type(r) == type(g) == type(b) == type(a) == int)
        else:
            raise ValueError, "Color must be 3- or 4-tuple, or #rrggbbaa"

        return color

    
    def _set_property_color(self, color):
        color = self._parse_color(color)
        if color != self["color"]:
            self._set_property_generic("color", color)
        return True

    def _validate_relative_value(self, val):
        """
        For _set_property_pos and _set_property_size, ensures the parameter
        is a valid value: either an integer, a percentage value, or "auto".
        If it is a stringified integer, it will convert to int type.
        """
        if type(val) == str:
            if val.replace("-", "").isdigit():
                val = int(val)
            elif re.sub("[\d%\-+]", "", val) and val != "auto":
                raise ValueError, "Invalid relative value '%s'" % val

        return val

    def _set_property_pos(self, pos):
        pos = [ self._validate_relative_value(x) for x in pos ]
        self._set_property_generic("pos", tuple(pos))

    def _set_property_size(self, size):
        size = [ self._validate_relative_value(x) for x in size ]
        self._set_property_generic("size", tuple(size))


    def _request_reflow(self, what_changed = None, old = None, new = None, child_asking = None):
        #print "[OBJECT REFLOW]", self, child_asking, what_changed, old, new
        if what_changed == "size":
            # TODO: only need to resync pos/clip if they depend on size.
            self._force_sync_property("pos")
            self._force_sync_property("clip")
            # Size changed, so cached value is dirty.
            self._dirty_cached_value("size")
            self.signals["resized"].emit(old, new)
        elif what_changed == "pos":
            self.signals["moved"].emit(old, new)
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
            if prop not in self._changed_since_sync:
                continue
            #print "  - prop", prop
            if self._can_sync_property(prop) != False and \
               getattr(self, "_sync_property_" + prop)() != False:
                needs_render = True
                # Prop could have been removed if sync handler called
                # _remove_sync_property()
                if prop in self._changed_since_sync:
                    del self._changed_since_sync[prop]

                updated_properties.append(prop)

        if self._changed_since_sync:
            # There are still some properties that haven't been synced.
            # Requeue this object for rendering.
            #print "Queueing rendering because", self._changed_since_sync
            self._queue_render()
        self._in_sync_properties = False
        return needs_render


    def _sync_property_pos(self):
        abs_pos = self._get_relative_values("pos")
        old_pos = self._o.geometry_get()[0]
        self._o.move(abs_pos)
        new_pos = self._o.geometry_get()[0]
        if old_pos != new_pos:
            if self._clip_object:
                clip_pos, clip_size = self._get_computed_clip()
                clip_pos = map(lambda x,y: x+y, clip_pos, abs_pos)
                self._clip_object.move(clip_pos)

            # Requesting a reflow is correct but slow.  Fix this.
            #self._request_reflow("pos", old_pos, new_pos)
            self.signals["moved"].emit(old_pos, new_pos)

    def _sync_property_visible(self):
        self._o.visible_set(self._get_relative_values("visible"))

    def _sync_property_display(self):
        self._sync_property_visible()
        if self["display"]:
            old_size = 0, 0
            new_size = self._get_computed_size()
        else:
            old_size = self._get_computed_size()
            new_size = 0, 0
        self._request_reflow("size", old_size, new_size)
    
    def _sync_property_layer(self):
        old_layer = self._o.layer_get()
        new_layer = self._get_relative_values("layer")
        if old_layer != new_layer:
            self._o.layer_set(new_layer)
            self._request_reflow("layer", old_layer, new_layer)

    def _sync_property_color(self):
        self._o.color_set(*self._get_relative_values("color"))

    def _sync_property_size(self):
        s = self._get_computed_size()
        # TODO: if s > size extents, add clip.
        old_size = self._o.geometry_get()[1]
        #print "[RESIZE OBJECT]", self, s
        self._o.resize(s)
        if s != old_size:
            self._request_reflow("size", old_size, s)

    def _sync_property_name(self):
        self._canvas._register_object_name(self["name"], self)

    def _sync_property_clip(self):
        if self["clip"] == None:
            if self._clip_object:
                # Object has been unclipped.
                if isinstance(sef._o, evas.Object):
                    self._o.clip_unset()
                self._clip_object = None
                self._apply_parent_clip()
            return

        # Object is clipped.
        if not self._clip_object:
            # Create new clip rectangle.
            self._clip_object = self.get_evas().object_rectangle_add()
            self._clip_object.show()
            self._apply_parent_clip()
            if isinstance(self._o, evas.Object):
                self._o.clip_set(self._clip_object)

        clip_pos, clip_size = self._get_computed_clip()
        clip_pos = map(lambda x,y: x+y, clip_pos, self._get_relative_values("pos"))

        self._clip_object.move(clip_pos)
        self._clip_object.resize(clip_size)

    def _sync_property_expand(self):
        if self._parent:
            self._parent._request_expand(self)

    def _sync_property_margin(self):
        pass

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

    def _remove_sync_property(self, prop):
        if prop in self._changed_since_sync:
            del self._changed_since_sync[prop]


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

    #
    # Position property methods
    #

    def move(self, left = None, top = None, right = None, bottom = None, hcenter = None, vcenter = None):
        if hcenter != None and (left != None or right != None):
            raise ValueError, "hcenter cannot be specified with left or right."
        if vcenter != None and (top != None or bottom != None):
            raise ValueError, "vcenter cannot be specified with top or bottom."

        # FIXME: right/bottom can be specified after left/top now.
        if left == right == hcenter == None:
            # No x position specified, so use old values.
            left, right, hcenter = self["pos"][0::2]
        if top == bottom == vcenter == None:
            # No y position specified, so use old values.
            top, bottom, vcenter = self["pos"][1::2]

        self["pos"] = left, top, right, bottom, hcenter, vcenter


    def get_computed_pos(self):
        return self._get_computed_pos()

    #
    # Getters and setters for position pseudo-properties.
    #


    def set_left(self, left):
        self.move(left = left)

    def get_left(self):
        return self["pos"][0]
    
    def set_top(self, top):
        self.move(top = top)

    def get_top(self):
        return self["pos"][1]

    def set_right(self, right):
        self.move(right = right)

    def get_right(self):
        return self["pos"][2]

    def set_bottom(self, bottom):
        self.move(bottom = bottom)

    def get_bottom(self):
        return self["pos"][3]

    def set_hcenter(self, hcenter):
        self.move(hcenter = hcenter)

    def get_hcenter(self):
        return self["pos"][4]

    def set_vcenter(self, vcenter):
        self.move(vcenter = vcenter)

    def get_vcenter(self):
        return self["pos"][5]


    #
    # color property methods
    #

    def set_color(self, r = None, g = None, b = None, a = None):
        # Handle the form set_color("#rrggbbaa")
        if isinstance(r, basestring):
            self["color"] = r
        else:
            self["color"] = (r, g, b, a)

    def get_color(self):
        return self["color"]

    def set_opacity(self, opacity):
        # Opacity can be 0-255 or 0.0-1.0
        if type(opacity) == float:
            opacity = int(opacity * 255)
        self["color"] = self["color"][:3] + [opacity]

    def get_opacity(self):
        return self["color"][3]


    #
    # visible property methods
    #

    def show(self):
        self.set_visible(True)

    def hide(self):
        self.set_visible(False)

    def set_visible(self, visible):
        self["visible"] = visible

    def get_visible(self):
        return self["visible"]

    def set_display(self, display):
        self["display"] = display

    def get_display(self):
        return self["display"]

    #
    # layerproperty methods
    #

    def set_layer(self, layer):
        self["layer"] = layer

    def get_layer(self):
        return self["layer"]


    #
    # size property methods
    #

    def resize(self, width = None, height = None):
        size = list(self["size"])
        assert(type(width) not in (list, tuple))
        assert(type(height) not in (list, tuple))
        if width != None:
            size[0] = width
        if height != None:
            size[1] = height
        
        self["size"] = size

    def set_width(self, width):
        self.resize(width = width)

    def get_width(self):
        return self["size"][0]

    def set_height(self, height):
        self.resize(height = height)

    def get_height(self):
        return self["size"][1]

    def get_size(self):
        return self["size"]

    def get_computed_size(self):
        return self._get_computed_size()


    #
    # clip property methods
    #

    def clip(self, pos = (0, 0), size = (0, 0)):
        if pos == "auto":
            self["clip"] = "auto"
        elif pos == None:
            self["clip"] = None
        else:
            self["clip"] = (pos, size)

    def unclip(self):
        self["clip"] = None

    def get_clip(self):
        return self["clip"]

    def set_clip(self, pos = (0, 0), size = (0, 0)):
        return self.clip(pos, size)


    #
    # name property methods
    #

    def get_name(self):
        return self["name"]

    def set_name(self, name):
        self["name"] = name


    #
    # expand property methods
    #

    def set_expand(self, expand):
        self["expand"] = expand

    def expand(self, expand):
        self.set_expand(expand)

    def get_expand(self):
        return self["expand"]


    def animate(self, method, **kwargs):
        return animation.animate(self, method, **kwargs)


    #
    # margin property methods
    #

    def set_margin(self, left = None, top = None, right = None, bottom = None):
        margin = left, top, right, bottom
        if None in margin:
            margin = tuple(map(lambda x, y: (x,y)[x==None], margin, self["margin"]))
        self["margin"] = margin

    def get_margin(self):
        return self["margin"]
