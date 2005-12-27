__all__ = [ 'Container' ]

import _weakref
from kaa.notifier import Signal
from object import *
from image import *
from rectangle import *
from text import *
import random

DEBUG = 0

class Container(Object):

    def __init__(self):
        self._children = []
        self._queued_children = {}
        super(Container, self).__init__()
        self["size"] = ("auto", "auto")
        self._debug_rect = None
        self._last_reflow_size = None

        self.signals.update({
            "reflowed": Signal()
        })

    def __str__(self):
        s = "<canvas.%s size=%s nchildren=%d>" % \
            (self.__class__.__name__, str(self["size"]), len(self._children))
        return s

    def _update_debug_rectangle(self):
        if not DEBUG or not self.get_evas():
            return
        if not self._debug_rect:
            self._debug_rect = self.get_evas().object_rectangle_add()
            self._debug_rect.show()
            self._debug_rect.color_set(random.randint(0, 255), random.randint(0, 255), random.randint(0, 255), 190)

        # For debugging, to be able to see the extents of the container.
        computed_size = self._get_computed_size()
        abs_pos = self._get_relative_values("pos")
        self._debug_rect.resize(computed_size)
        self._debug_rect.move(abs_pos)
        self._debug_rect.layer_set(self._get_relative_values("layer")+1)

        print "DRAW DEBUG RECT", self, abs_pos, computed_size


    def _canvased(self, canvas):
        super(Container, self)._canvased(canvas)
        for child in self._children:
            child._canvased(canvas)


    def _restack_children(self):
        last_object = None
        for child in self._children:
            if child._o:
                if last_object:
                    child._o.stack_above(last_object)
                last_object = child._o

    def _uncanvased(self):
        super(Container, self)._uncanvased()
        for child in self._children:
            child._uncanvased()


    def _set_property_generic(self, key, value):
        super(Container, self)._set_property_generic(key, value)

        if key not in ("name",):
            #self._queue_children_sync_property(key)
            self._force_sync_property(key)

    def _force_sync_property(self, prop, exclude = None, update_children = True):
        super(Container, self)._force_sync_property(prop)
        if update_children:
            for child in self._children:
                if exclude != child:
                    child._force_sync_property(prop)
        self._queue_render()


    def _request_reflow(self, what_changed = None, old = None, new = None, child_asking = None, signal = True):
        if what_changed == "layer":
            self._restack_children()
            return

        if "auto" not in self["size"]:
            # TODO: with fixed dimensions, there shouldn't be any need to
            # reflow.  Check into this.
            raise Exception
            pass

        last = self._last_reflow_size
        size = self._get_actual_size()
        size_changed = size != self._last_reflow_size
        self._last_reflow_size = size

        # Only need to reflow if our size has changed.
        if not size_changed:
            return False

        #print "[CONTAINER REFLOW]: size_changed=%s lastsize=%s cursize=%s, size=%s " % \
        # (str(size_changed), str(last), str(size), str(self["size"])), self, child_asking, what_changed, old, new
        self._force_sync_property("size", update_children = False)
        self._force_sync_property("clip", update_children = False)
        if None in self._get_fixed_pos():
            # Our position depends on our size, so we need to resync our
            # pos.
            self._force_sync_property("pos", update_children = False)

        for child in self._children:
            if None in child._get_fixed_pos():
                # Child position depends on our size, so update its pos.
                child._force_sync_property("pos")

            if None in child._get_fixed_size(resolve_auto = False):
                # Child's size depends on our size, so update its size.
                child._force_sync_property("size")
                child._force_sync_property("clip")

        if signal:
            self.signals["reflowed"].emit()

        if self._parent:
            self._parent._request_reflow(child_asking = self)

        return True

    def _request_expand(self, child_asking):
        pass
    
    def _queue_render(self, child = None):
        if child:
            w = _weakref.ref(child)
            #w = child
            if w in self._queued_children:
                return

            self._queued_children[w] = 1

        super(Container, self)._queue_render(child)


    def _render_queued(self):
        #print "[render queued]", self, self._queued_children
        if len(self._queued_children) == 0:
            return False

        needs_render = False
        updated_properties = []
        while self._queued_children:
            #print "[render loop]", self, self._queued_children
            queued_children = self._queued_children
            self._queued_children = {}
            if self._sync_properties(updated_properties):
                needs_render = True

            changed = False
            for child in queued_children.keys():
                child = child()  # Resolve weakref
                if not child:
                    continue

                if isinstance(child, Container) and child != self:
                    if child._render_queued():
                        changed = needs_render = True
                if child._sync_properties():
                    changed = needs_render = True

            if not changed:
                break

        if "size" in updated_properties or "pos" in updated_properties:
            self._update_debug_rectangle()

        #print "[render exit]", self, self._queued_children, needs_render
        return needs_render
        


    def _sync_property_clip(self):
        super(Container, self)._sync_property_clip()
        if not self._children:
            # Hide clip object if there are no children (otherwise it will
            # just be rendered as a visible white rectangle.)
            self._clip_object.hide()
        else:
            self._apply_clip_to_children()


    def _can_sync_property(self, property):
        return self.get_canvas() != None

    def _sync_property_pos(self):
        self._sync_property_size()
        self._sync_property_clip()
        self.signals["moved"].emit(None, None)
        return True

    def _sync_property_color(self):
        return True

    def _sync_property_visible(self):
        return True

    def _sync_property_layer(self):
        return True

    def _sync_property_size(self):
        return True

    def _set_property_size(self, size):
        super(Container, self)._set_property_size(size)
        # Position of children may also depend on our size, so recalculate
        # and sync positions of children.
        self._force_sync_property("pos")

    def _apply_clip_to_children(self):
        for child in self._children:
            if isinstance(child, Container):
                child._apply_clip_to_children()
            else:
                child._apply_parent_clip()


    def _reset(self):
        super(Container, self)._reset()
        for child in self._children:
            child._reset()


    def _get_actual_size(self, child_asking = None):
        size = [0, 0]
        for child in self._children:
            if child_asking:
                child_pos = child._get_fixed_pos()
                # Replace None values with 0 in fixed pos
                child_pos = [ (x, 0)[x == None] for x in child_pos ]
            else:
                child_pos = child._get_computed_pos()

            child_size = child._get_actual_size()
            for i in range(2):
                if child_pos[i] + child_size[i] > size[i]:
                    size[i] = child_pos[i] + child_size[i]

        # If container has a fixed dimension, override calculated dimension.
        for i in range(2):
            if type(self["size"][i]) == int:
                size[i] = self["size"][i]
        return size

    def _get_minimum_size(self):
        size = [0, 0]
        for child in self._children:
            child_pos = child._get_fixed_pos()
            # Replace None values with 0 in fixed pos
            child_pos = [ (x, 0)[x == None] for x in child_pos ]
            child_size = child._get_minimum_size()

            for i in range(2):
                if child_pos[i] + child_size[i] > size[i]:
                    size[i] = child_pos[i] + child_size[i]
 
        # If container has a fixed dimension, override calculated dimension.
        for i in range(2):
            if type(self["size"][i]) == int:
                size[i] = self["size"][i]
        return size


    def _compute_size(self, size, child_asking, extents = None):
        if child_asking:
            if "auto" in size:
                size = list(size)  # copy
                actual_size = self._get_actual_size(child_asking)
                if size[0] == "auto":
                    size[0] = actual_size[0]
                if size[1] == "auto":
                    size[1] = actual_size[1]

        return super(Container, self)._compute_size(size, child_asking, extents)


    def _get_extents(self, child_asking = None):
        if not child_asking:
            return super(Container, self)._get_extents()

        size = list(self["size"])
        if type(size[0]) == type(size[1]) == int:
            return size
        if "auto" in size:
            if self._parent:
                extents = self._parent._get_extents(child_asking = self)
            else:
                extents = 0, 0

            if size[0] == "auto":
                size[0] = extents[0]
            if size[1] == "auto":
                size[1] = extents[1]

        return self._compute_size(size, child_asking)


    #
    # Public API
    #

    def add_child(self, child, **kwargs):
        assert(isinstance(child, Object))
        if child._parent:
            raise CanvasError, "Attempt to parent an adopted child."

        supported_kwargs = "visible", "color", "name", "layer", "clip",  \
                           "expand", "font", "aspect", "size", "left", "top", \
                           "right", "bottom", "vcenter", "hcenter", "width", \
                           "height"
        for kwarg in kwargs.keys():
            if kwarg not in supported_kwargs:
                raise ValueError, "Unsupported kwarg '%s'" % kwarg

        child.move(left = kwargs.get("left"), top = kwargs.get("top"),
                   right = kwargs.get("right"), bottom = kwargs.get("bottom"),
                   hcenter = kwargs.get("hcenter"), vcenter = kwargs.get("vcenter"))
        child.resize(kwargs.get("width"), kwargs.get("height"))

        if "visible" in kwargs:
            child.set_visible(kwargs["visible"])
        if "color" in kwargs:
            if type(kwargs["color"]) == str:  # html-style color spec
                child.set_color(kwargs["color"])
            else:
                child.set_color(*kwargs["color"])
        if "name" in kwargs:
            child.set_name(kwargs["name"])
        if "layer" in kwargs:
            child.set_layer(kwargs["layer"])
        if "clip" in kwargs:
            if type(kwargs["clip"]) in (tuple, list):
                child.clip(*kwargs["clip"])
            else:  # "auto" or None
                child.clip(kwargs["clip"])
        if "expand" in kwargs:
            child.expand(kwargs["expand"])

        if ("font" in kwargs or "size" in kwargs) and isinstance(child, Text):
            child.set_font(kwargs.get("font"), kwargs.get("size"))
        if "aspect" in kwargs and isinstance(child, Image):
            child.set_aspect(kwargs["aspect"])

        self._children.append(child)
        child._adopted(self)
        if self.get_canvas():
            child._canvased(self.get_canvas())

        if self._clip_object:
            self._clip_object.show()

        return child


    def remove_child(self, child):
        if child not in self._children:
            raise ValueError, "Child not found"
        self._children.remove(child)
        child.hide()
        child._queue_render()
        if isinstance(child, Container):
            child._queued_children = {}

        # FIXME: shouldn't access _queued_children directly (create an 
        # unqueue method)
        if child._canvas and child in child._canvas._queued_children:
            del child._canvas._queued_children[child]
        child._orphaned()
        if self._clip_object and not self._children:
            # Hide clip object if there are no children (otherwise it will
            # just be rendered as a visible white rectangle.)
            self._clip_object.hide()
            
        self._request_reflow()

        return True


    def kidnap(self, child):
        """
        Forces a child to be added even if it's adopted by another parent.
        """
        if child.get_parent():
            child.get_parent().remove_child(child)
        if child.get_canvas() != self.get_canvas():
            child._uncanvased()
            child._reset()
        self.add_child(child)
 
 
    def get_child_position(self, child):
        """
        Returns the child's position relative to the container.
        """
        # Not the most efficient way to calculate this ...
        abs_child_pos = child._get_relative_values("pos")
        abs_pos = self._get_relative_values("pos")
        return abs_child_pos[0] - abs_pos[0], abs_child_pos[1] - abs_pos[1]

        
        
    # Convenience functions for object creation.


    def add_container(self, **kwargs):
        return self.add_child(Container(), **kwargs)

    def add_image(self, image, **kwargs):
        return self.add_child(Image(image), **kwargs)

    def add_text(self, text = None, **kwargs):
        return self.add_child(Text(text), **kwargs)

    def add_rectangle(self, **kwargs):
        return self.add_child(Rectangle(), **kwargs)

