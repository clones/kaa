__all__ = [ 'Container' ]


import _weakref
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
        self._debug_rect.layer_set(self._get_relative_values("layer"))


    def _canvased(self, canvas):
        super(Container, self)._canvased(canvas)
        for child in self._children:
            child._canvased(canvas)


    def _uncanvased(self):
        super(Container, self)._uncanvased()
        for child in self._children:
            child._uncanvased()


    def _set_property_generic(self, key, value):
        super(Container, self)._set_property_generic(key, value)

        if key not in ("name",):
            #self._queue_children_sync_property(key)
            self._force_sync_property(key)

    def _force_sync_property(self, prop, exclude = None):
        super(Container, self)._force_sync_property(prop)
        for child in self._children:
            if exclude != child:
                child._force_sync_property(prop)
        self._queue_render()


    def _request_reflow(self, what_changed = None, old = None, new = None, child_asking = None):
        # TODO: only need to sync children whose pos or size are relative to
        # our size.
        #print "[CONTAINER REFLOW]", self, child_asking, what_changed, old, new
        self._force_sync_property("pos", exclude = child_asking)
        self._force_sync_property("size", exclude = child_asking)
        # TODO: if our size changes as a result, need to propage reflow to parent
        if self._parent:
            self._parent._request_reflow(child_asking = self)


    def _request_expand(self, child_asking):
        pass
    
    def _queue_render(self, child = None):
        if child:
            #w = _weakref.ref(child)
            w = child
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
        self._set_property_generic("size", size)
        # Position of children may also depend on our size, so recalculate
        # and sync positions of children.
        self._force_sync_property("pos")

    def _apply_clip_to_children(self):
        for child in self._children:
            if type(child) == Container:
                child._apply_clip_to_children()
            else:
                child._apply_parent_clip()


    def _reset(self):
        super(Container, self)._reset()
        for child in self._children:
            child._reset()


    def _get_actual_size(self, child_asking = None):
        w, h = 0, 0
        for child in self._children:
            if child_asking:
                pos = [0, 0]
                if type(child["pos"][0]) == int:
                    pos[0] = child["pos"][0]
                if type(child["pos"][1]) == int:
                    pos[1] = child["pos"][1]
            else:
                pos = child._get_computed_pos()

            size = child._get_actual_size()
            if pos[0] + size[0] > w:
                w = pos[0] + size[0]
            if pos[1] + size[1] > h:
                h = pos[1] + size[1]

        return w, h

    def _get_minimum_size(self):
        if type(self["size"][0]) == type(self["size"][1]) == int:
            return self["size"]

        w, h = 0, 0
        for child in self._children:
            pos = [0, 0]
            if type(child["pos"][0]) == int:
                pos[0] = child["pos"][0]
            if type(child["pos"][1]) == int:
                pos[1] = child["pos"][1]

            size = child._get_minimum_size()
            if pos[0] + size[0] > w:
                w = pos[0] + size[0]
            if pos[1] + size[1] > h:
                h = pos[1] + size[1]
        
        if type(self["size"][0]) == int:
            w = self["size"][0]   
        if type(self["size"][1]) == int:
            h = self["size"][1]   
        return w,h


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
        if child._parent:
            raise CanvasError, "Attempt to parent an adopted child."

        if "pos" in kwargs:
            child.move(kwargs["pos"])
        if "visible" in kwargs:
            child.set_visible(kwargs["visible"])
        if "color" in kwargs:
            child.set_color(*kwargs["color"])
        if "name" in kwargs:
            child.set_name(kwargs["name"])
        if "layer" in kwargs:
            child.set_layer(kwargs["layer"])
        if "clip" in kwargs:
            child.clip(*kwargs["clip"])
        if "size" in kwargs and not isinstance(child, Text):
            child.resize(kwargs["size"])
        if ("font" in kwargs or "size" in kwargs) and isinstance(child, Text):
            child.set_font(kwargs.get("font"), kwargs.get("size"))
        if "expand" in kwargs:
            child.expand(kwargs["expand"])

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
     
        
    # Convenience functions for object creation.


    def add_container(self, **kwargs):
        return self.add_child(Container(), **kwargs)

    def add_image(self, image, **kwargs):
        return self.add_child(Image(image), **kwargs)

    def add_text(self, text = None, **kwargs):
        return self.add_child(Text(text), **kwargs)

    def add_rectangle(self, **kwargs):
        return self.add_child(Rectangle(), **kwargs)

