import kaa.notifier, kaa.evas
from kaa.weakref import weakref
import time, logging

try:
    from kaa import imlib2
except ImportError:
    imlib2 = None

log = logging.getLogger('candy')

SYNC_NOOP         = 0
SYNC_NEEDS_RENDER = 1
SYNC_NOT_FINISHED = 2
SYNC_SIZE_CHANGED = 4

class CanvasError(Exception):
    pass

def debug(*args, **kwargs):
    return
    for arg in args:
        print arg,
    if kwargs.get('lf', True):
        print

class Object(object):

    @classmethod
    def _add_properties(cls, prepend = (), append = ()):
        """
        Adds new properties to the class object, appending or prepending to
        the current list (of the superclass), removing any duplicates.  This
        is done as a class method because properties are constant for all
        instances of a clsas, so there's no sense in incurring the overhead
        of allocating the property list during instantiation.
        """
        cur_properties = ()
        if hasattr(cls, "_property_list"):
            cur_properties = cls._property_list

        # Current property list with new prepend/append properties removed.
        props = [ x for x in cur_properties if x not in prepend and x not in append ]
        # Now construct the new list.
        cls._property_list = prepend + tuple(props) + append
        # Dict that maps each property to its index in the property list
        # for sorting purposes.
        cls._property_list_index = dict(zip(cls._property_list, range(len(cls._property_list))))


    def __init__(self, **kwargs):
        self.signals = {
        }

        # Dict that holds all property values before they have been computed.
        self._properties = {}

        # Dict that holds all computed property values.  Property names
        # suffixed with -abs are the absolute computed value for that 
        # property.  (That is, the value that evas is told.)
        self._computed_properties = {}

        # Dict that holds property names that require recomputing and syncing;
        # dictionary used instead of list for faster lookup.
        self._dirty_properties = {}

        # True if we've already queued a property sync.
        self._is_sync_queued = False

        # True if we're currently inside _sync_dirty_properties()
        self._is_currently_syncing = False

        # The underlying evas object.
        self._o = None
        # An evas object used as our clip object.
        self._clip_object = None
        # Weak reference to the top-level canvas object (i.e. the canvas itself)
        self._canvas = None
        # Weak reference to our parent.
        self._parent = None

        self['name'] = kwargs.get('name')
        self['visible'] = kwargs.get('visible', True)
        self['opacity'] = kwargs.get('opacity', 1.0)
        self['color'] = kwargs.get('color', (255, 255, 255))
        self['passive'] = kwargs.get('passive', False)
        self['margin'] = kwargs.get('margin', (0, 0, 0, 0))
        self['padding'] = kwargs.get('padding', (0, 0, 0, 0))
        self['size'] = kwargs.get('width', 'auto'), kwargs.get('height', 'auto')
        if 'size' in kwargs:
            self['size'] = kwargs.get('size', ('auto', 'auto'))

        self['pos'] = kwargs.get('left', 0), kwargs.get('top', 0), \
                      kwargs.get('right'), kwargs.get('bottom'), \
                      kwargs.get('hcenter'), kwargs.get('vcenter')
        if 'pos' in kwargs:
            self['pos'] = tuple(kwargs.get('pos')) + (None, None, None, None)


    def __repr__(self):
        s = '<%s object' % self.__class__.__name__
        if self['name']:
            s += ' "%s"' % self['name']
        return s + '>'


    def __getitem__(self, key):
        return self._properties.get(key)


    def __delitem__(self, key):
        try:
            del self._properties[key]
        except KeyError:
            pass


    def __setitem__(self, key, value):
        key = key.replace('-', '_')
        if self._properties.get(key) == value:
            return

        set_func = getattr(self, "_set_property_" + key, self._set_property_generic)
        value = set_func(key, value)
        if value is not None:
            self._set_property_generic(key, value)


    def _set_property_generic(self, key, value):
        self._properties[key] = value
        if key not in ('name',):
            self._dirty_property(key)


    def _dirty_property(self, prop):
        """
        Marks a property as dirty, meaning the property value we have is out-
        of-sync with the property on the canvas.  Next mainloop step, the 
        property will be synced and the canvas rerendered if necessary.  Any
        cached computed values for this property will also be deleted, forcing
        them to be recalculated next time they are needed.
        """
        if prop in self._dirty_properties:
            return

        try:
            self._dirty_properties[prop] = self._property_list_index[prop]
        except KeyError:
            raise ValueError, "Unknown property '%s'" % prop

        if prop in self._computed_properties:
            self._computed_properties['last-' + prop] = self._computed_properties[prop]
            del self._computed_properties[prop]
        prop_abs = prop + '-abs'
        if prop_abs in self._computed_properties:
            self._computed_properties['last-' + prop_abs] = self._computed_properties[prop_abs]
            del self._computed_properties[prop_abs]
        self._queue_sync()


    def _undirty_property(self, prop):
        """
        Marks a property as no longer dirty.  Called when the property has just
        been synchronized, or possibly when another property has just been 
        synchronized and it happened to take care of this one.
        """
        try:
            del self._dirty_properties[prop]
        except KeyError:
            pass


    def _create_evas_object(self, evas):
        """
        Creates the underlying Evas object and returns it.  To be implemented 
        by subclasses.
        """
        pass


    def _queue_sync(self):
        """
        Requests from our parent that _sync_dirty_properties be called on the next
        main loop step.
        """
        if not self._is_sync_queued and self._parent:
            #print "queue_sync", self, self._parent, self._is_sync_queued
            self._parent._queue_sync(self)
            self._is_sync_queued = True


    def _adopted(self, parent):
        """
        Called by our parent when we get adopted.
        """
        if self._parent == parent:
            return

        # Hold a weakref to our parent.
        self._parent = weakref(parent)
        # Since we have a new parent we must resynchronize all our properties
        # (because many of them may be relative to our parent).  So we flag
        # all properties as dirty, which indirectly will queue us for resync.
        self._dirty_all_properties()


    def _canvased(self, canvas):
        """
        Called by our parent container when the top-most ancestor is a Canvas
        object.
        """
        if canvas == self._canvas:
            return

        # Hold a weakref to the canvas.
        self._canvas = weakref(canvas)
        if self["name"]:
            self._canvas._register_object_name(self["name"], self)

        evas = canvas.get_evas()
        if not self._o and evas:
            o = self._create_evas_object(evas)
            self._wrap(o)



    def _uncanvased(self):
        """
        Called by our parent when we're detached from our current canvas.
        """
        if self["name"] and self._canvas:
            self._canvas._unregister_object_name(self["name"])
        self._wrap(None)
        self._canvas = None



    def _wrap(self, evas_object):
        """
        Called when our underlying evas object has been created.  Before now
        we couldn't sync any properties because we had nothing to sync to.
        """
        self._o = evas_object
        self._clip_object = None
        if not self._o:
            return

        self._dirty_all_properties()


    def _dirty_all_properties(self):
        """
        Declare all properties dirty (i.e. require syncing to evas object) and
        queue propeties sync.  Usually done when we get a new parent.
        """
        self._dirty_properties = self._property_list_index.copy()
        self._queue_sync()


    def _can_sync_property(self, property):
        """
        Called just before we are about to sync a property; if this method
        returns False then we defer the sync.
        """
        return self._o != None or property == "name"


    def _sync_dirty_properties(self, debug_prefix = ''):
        """
        Synchronizes all dirty properties with the internal evas object.
        Not all properties may be able to be synchronized, in which case
        they will not be removed from _dirty_properties.  

        This function returns a bitmap that may comprise of:
            SYNC_NEEDS_RENDER 
                - property that affects visual appearance has been updated.
            SYNC_NOT_FINISHED 
                - one or more properties weren't synchronized so we need to
                  be called again.
        """
        # XXX: this method is a performance hotspot.

        assert(not self._is_currently_syncing)
        self._is_currently_syncing = True
        return_value = 0
        debug(debug_prefix, "* sync:", self, " ".join(self._dirty_properties.keys()))
        # Keep syncing dirty properties until we either have no more dirty
        # properties left, or all the properties we tried to sync either 
        # aren't ready to be synced yet (_can_sync_property() return False)
        # or they all returned SYNC_NOT_FINISHED.
        #
        # This allows a property sync function to dirty a new property, and
        # that new property will get synced in this iteration.
        while self._dirty_properties:
            updated = False

            # _dirty_propetries is a dict of prop:index where index is the
            # property's position in the property list.  We sort the
            # dirty properties based on this index so we sync dirty properties
            # in the proper order.  This is slightly faster than iterating
            # over the full property list and testing if the property exists
            # in the _dirty_properties dict.  It also has the benefit of
            # scaling independently of the number of properties in the property
            # list.
            for prop in sorted(self._dirty_properties.keys(), key=self._dirty_properties.get):
                debug(debug_prefix, "   prop=%s can_sync=%s ->" % (prop, self._can_sync_property(prop)), lf=False)
                if self._can_sync_property(prop):
                    try:
                        result = getattr(self, "_sync_property_" + prop)()
                    except:
                        log.exception("Exception when syncing property '%s' for %s" % (prop, self))
                        result = 0

                    # If property indicates canvas needs rendering, propagate
                    # this flag back up to our parent.
                    return_value |= result & (SYNC_NEEDS_RENDER | SYNC_SIZE_CHANGED)

                    if not result & SYNC_NOT_FINISHED:
                        # Property sync successful, so remove this property from the
                        # list of dirty properties.
                        del self._dirty_properties[prop]
                        updated = True

                debug()

            if not updated:
                # No dirty property was cleared this iteration.  It means that
                # none of our dirty properties are ready to be synced, or that
                # they all returned SYNC_NOT_FINISHED.  In any case, we can't
                # go any further so we break out.
                break

        if len(self._dirty_properties):
            # We still have dirty properties, so we indicate to our parent
            # that we're not done syncing. This method will get called again
            # on the next mainloop iteration.
            return_value |= SYNC_NOT_FINISHED

        self._is_currently_syncing = False
        return return_value



    def _compute_relative_value(self, val, max):
        """
        Resolves a relative value into an numeric value.  Values that are
        already numeric will be be returned as-is (converted from a string
        first, if necessary).  If val is a percentage, it will be computed
        against max.
        """
        if isinstance(val, str):
            if val.replace("-", "").isdigit():
                return int(val)
            elif "%" in val:
                return int(float(val.replace("%", "")) / 100.0 * max)
            else:
                raise ValueError, "Invalid relative value '%s'" % val
        return val


    def _get_extents(self):
        """
        Returns a 2-tuple containing the numeric width and height that
        defines the maximum size this object can hold.  
        """
        return self._parent._get_computed_property_for_child('extents', self)


    def _get_intrinsic_size(self):
        """
        Returns the intrinsic size of the object.  The intrinsic size is the
        object's actual or native size, and its definition varies depending on
        the object.

        If the intrinsic size is not yet known, (0, 0) will be returned.
        This can happen, for example, when an Image object is created but
        it hasn't yet synchronized (and therefore loaded the image).

        Returns a 2-tuple of integers, width and height.
        """
        # Implemented by subclass.
        return 0, 0



    def _get_computed_size(self):
        """
        Returns the object's computed size.  The computed size is the size
        of the object as it appears on the canvas, including padding.  (This
        therefore implements a traditional box model and not the W3C box
        model.)  Relative (percentage) values are resolved into numeric 
        values.

        If a dimension is not able to be calculated when this method is 
        called, then 0 will be returned for that dimension.  

        Returns a 2-tuple of integers, width and height.
        """
        size = self._computed_properties.get('size')
        if size:
            return size

        size = list(self["size"])
        extents = self._get_extents()

        if 'auto' in size:
            # At least one of our dimensions is 'auto', so prefetch our
            # intrinsic size.
            intrinsic_size = list(self._get_intrinsic_size())
            # Also fetch our padding, which is added to the intrinsic size.
            padding = self._get_computed_padding()
            padding_xy = (padding[1] + padding[3], padding[0] + padding[2])
        else:
            # Dummy value to placate the interpreter; not used.
            padding_xy = intrinsic_size = None

        for index in range(2):
            if size[index] == "auto":
                # 'auto' dimensions are intrinsic size plus padding.
                size[index] = intrinsic_size[index] + padding_xy[index]
            else:
                # Fixed and relative sizes are based on our extents, which
                # implicitly includes padding.
                size[index] = self._compute_relative_value(size[index], extents[index])


        size = tuple(size)
        self._computed_properties['size'] = size
        return size


    def _get_computed_padding(self):
        """
        Returns the padding of the object.  Relative values are computed
        and a 4-tuple of integers is returned, representing the top, right,
        bottom, and left padding respectively.
        """
        if 'padding' in self._computed_properties:
            return self._computed_properties['padding']

        extents = self._get_extents()

        padding = list(self['padding'])
        # Top
        padding[0] = self._compute_relative_value(padding[0], extents[1])
        # Right
        padding[1] = self._compute_relative_value(padding[1], extents[0])
        # Bottom
        padding[2] = self._compute_relative_value(padding[2], extents[1])
        # Left
        padding[3] = self._compute_relative_value(padding[3], extents[0])
        self._computed_properties['padding'] = padding
        return tuple(padding)



    def _get_computed_margin(self):
        """
        Returns the margin of the object.  Relative values are computed
        and a 4-tuple of integers is returned, representing the top, right,
        bottom, and left padding respectively.
        """
        if 'margin' in self._computed_properties:
            return self._computed_properties['margin']

        extents = self._get_extents()

        margin = list(self['margin'])
        # Top
        margin[0] = self._compute_relative_value(margin[0], extents[1])
        # Right
        margin[1] = self._compute_relative_value(margin[1], extents[0])
        # Bottom
        margin[2] = self._compute_relative_value(margin[2], extents[1])
        # Left
        margin[3] = self._compute_relative_value(margin[3], extents[0])
        self._computed_properties['margin'] = margin
        return tuple(margin)


    def _get_computed_position(self):
        """
        Returns a 2-tuple of integers indicating the object's computed
        left and top position (in pixels) relative to the parent.
        """
        if 'pos' in self._computed_properties:
            return self._computed_properties['pos']

        extents = self._get_extents()

        pos = list(self['pos'])
        margin = self._get_computed_margin()

        for index in range(2):
            pos[index] = self._compute_relative_value(pos[index], extents[index])
        pos = pos[0] + margin[3], pos[1] + margin[0]
        
        self._computed_properties['pos'] = pos
        return pos



    ########################################################################
    # Properties
    ########################################################################


    def _sync_property_name(self):
        return SYNC_NOOP


    def _compute_absolute_visible(self):
        parent_visible = self._parent._get_computed_property_for_child('visible-abs', self, True)
        visible = parent_visible and self['visible']
        self._computed_properties['visible-abs'] = visible
        return visible

    def _sync_property_visible(self):
        visible = self._compute_absolute_visible()
        if visible:
            self._o.show()
        else:
            self._o.hide()
        return SYNC_NEEDS_RENDER


    def _compute_absolute_opacity(self):
        parent_opacity = self._parent._get_computed_property_for_child('opacity-abs', self, 1.0)
        opacity = parent_opacity * self['opacity']
        self._computed_properties['opacity-abs'] = opacity
        return opacity

    def _sync_property_opacity(self):
        self._compute_absolute_opacity()
        # We could do _dirty_property('color') here, which will call
        # _sync_property_color indirectly, but this will delete color-abs
        # from computed properties and require us to compute it again, which
        # is wasteful as the only thing that has changed is the opacity.
        # Instead we will call _sync_property_color() directly in order to
        # reuse the current and perfectly valid color-abs computed property.
        return self._sync_property_color()


    def _set_property_color(self, dummy, color):
        """
        Parse a color that is either a 3-tuple of integers specifying red,
        green, and blue (between 0 and 255), or an html-spec such as #rrggbb
        or #rgb.
        """
        if isinstance(color, basestring) and color[0] == '#' and len(color) in (4, 7):
            if len(color) == 4:
                return int(color[1], 16) * 17, int(color[2], 16) * 17, int(color[3], 16) * 17
            else:
                return int(color[1:3], 16), int(color[3:5], 16), int(color[5:7], 16)

        elif isinstance(color, (list, tuple)):
            # If any color element is none, us the existing value.
            if None in color:
                color = tuple(map(lambda x, y: (x,y)[x==None], color, self["color"]))
            return color
        else:
            raise ValueError, "Color must be a 3-tuple or html-style #rrggbb"

            
    def _compute_absolute_color(self):
        if 'color-abs' in self._computed_properties:
            # If color-abs exists in computed properties, return that instead
            # of reblending.  This will happen when opacity changes but color
            # does not; we need to indirectly sync the color property (because
            # opacity is just alpha color to evas), but it isn't necessary to 
            # recompute absolute color.
            return self._computed_properties['color-abs']

        def _blend_pixel(a, b):
            tmp = (a * b) + 0x80
            return (tmp + (tmp >> 8)) >> 8

        parent_color = self._parent._get_computed_property_for_child('color-abs', self, (255, 255, 255))
        color = self['color']
        abs_color = _blend_pixel(color[0], parent_color[0]), \
                    _blend_pixel(color[1], parent_color[1]), \
                    _blend_pixel(color[2], parent_color[2])

        self._computed_properties['color-abs'] = abs_color
        return abs_color


    def _sync_property_color(self):
        opacity = self._computed_properties['opacity-abs']
        color = self._compute_absolute_color()
        color = color + (int(opacity * 255),)
        self._o.color_set(*color)
        return SYNC_NEEDS_RENDER


    def _sync_property_passive(self):
        # FIXME: only do properties that are affected by passive property;
        # a property is affected if calls get_extents (i.e. uses a relative
        # value in the property.
        self._dirty_property("margin")
        self._dirty_property("padding")
        self._dirty_property("size")
        self._dirty_property("pos")

        return SYNC_NOOP


    def _sync_property_margin(self):
        # Margin affects outer pos, and therefore also inner pos.  Need
        # to resync pos.
        self._dirty_property("pos")
        return SYNC_NOOP


    def _sync_property_padding(self):
        # Padding affects inner size, which is the canvas size.
        self._dirty_property("size")
        # Padding also changes inner position, so we must resync pos as well.
        self._dirty_property("pos")
        return SYNC_NOOP


    def _sync_property_size(self):
        if self['pos'][2:] != (None, None, None, None) and self['passive']:
            # Our position depends on our size, so cause pos resync.
            self._dirty_property('pos')
        size = self.get_computed_inner_size()
        debug("inner size", size, lf = False)
        self._o.resize(size)
        return SYNC_NEEDS_RENDER | SYNC_SIZE_CHANGED


    def _set_property_pos(self, dummy, pos):
        return tuple(pos)


    def _compute_absolute_pos(self):
        parent_pos = self._parent._get_computed_property_for_child('pos-inner-abs', self, (0, 0))
        pos = self._get_computed_position()
        padding = self._get_computed_padding()

        # Store border position (this includes margin)
        abs_pos = pos[0] + parent_pos[0], pos[1] + parent_pos[1]
        self._computed_properties['pos-abs'] = abs_pos

        # Store inner position (add padding)
        abs_inner_pos = abs_pos[0] + padding[3], abs_pos[1] + padding[0]
        self._computed_properties['pos-inner-abs'] = abs_inner_pos
        return abs_inner_pos


    def _sync_property_pos(self):
        # Sync the object to the absolute inner position.
        abs_pos = self._compute_absolute_pos()
        debug("abs pos", abs_pos, lf = False)
        self._o.move(abs_pos)
        return SYNC_NEEDS_RENDER


    ########################################################################
    # Public API
    ########################################################################


    def get_computed_size(self):
        """
        Public wrapper for _get_computed_size().  If caller asks for computed
        size of the object before we've synced properties, we implicitly
        sync the canvas, which calculates layout, which is necessary in order
        to get the computed size.
        """
        if not self._canvas:
            return 0, 0
        if not self._is_currently_syncing and self._is_sync_queued:
            # TODO: this syncs the whole canvas which might not be needed.  
            # Only need to sync objects that would affect our size.
            self._canvas._sync_dirty_properties()

        return self._get_computed_size()



    def get_computed_inner_size(self):
        """
        Returns the computed inner size of the object.  The inner size is 
        the computed size of the object less its padding.
        """
        size = self.get_computed_size()
        padding = self._get_computed_padding()
        size = size[0] - padding[1] - padding[3], \
               size[1] - padding[0] - padding[2]
        self._computed_properties['size-inner'] = size
        return size



    def get_computed_outer_size(self):
        """
        Returns the computed outer size of the object.  The outer size is 
        the computed size of the object plus its margin.
        """
        size = self.get_computed_size()
        margin = self._get_computed_margin()
        return size[0] + margin[1] + margin[3], \
               size[1] + margin[0] + margin[2]



    def get_computed_position(self):
        """
        Public wrapper for _get_computed_position().  Like computed size, all
        objects affecting our position must first be synced before we can
        correctly compute position.
        """
        if not self._is_currently_syncing and self._is_sync_queued:
            if not self._canvas:
                return 0, 0

            # TODO: this syncs the whole canvas which might not be needed.  
            # Only need to sync objects that would affect our size.
            self._canvas._sync_dirty_properties()

        return self._get_computed_position()


    def get_computed_inner_position(self):
        pos = self.get_computed_position()
        padding = self._get_computed_padding()
        return pos[0] + padding[3], pos[1] + padding[0]


    def get_computed_outer_position(self):
        pos = self.get_computed_position()
        margin = self._get_computed_margin()
        return pos[0] - margin[3], pos[1] - margin[0]


    def resize(self, size):
        self["size"] = size


    def move(self, pos):
        self['pos'] = pos


    def get_canvas(self):
        return self._canvas


Object._add_properties(
    # Properties will be synchronized in the order they appear in
    # this list.
            #"name", "expand", "visible", "display", "layer",
            #"color", "size", "pos", "clip", "margin", "padding"
    ('name', 'visible', 'opacity', 'color', 'passive', 
    'margin', 'padding', 'size', 'pos',
#    'width', 'height', 'left', 'top', 'right', 'bottom', 'vcenter', 'hcenter',
#    'margin_left', 'margin_top', 'margin_bottom', 'margin_right',
#    'padding_left', 'padding_top', 'padding_bottom', 'padding_right'
    
    )
)


class Rectangle(Object):

    def __init__(self, **kwargs):
        super(Rectangle, self).__init__(**kwargs)


    def _create_evas_object(self, evas):
        """
        Creates the actual evas Rectangle object.  Called when canvased.
        """
        return evas.object_rectangle_add()



class Image(Object):

    def __init__(self, image_or_file = None, **kwargs):
        super(Image, self).__init__(**kwargs)


        self._loaded = False
        if image_or_file:
            self.set_image(image_or_file)



    def _create_evas_object(self, evas):
        """
        Creates the actual evas Image object.  Called when canvased.
        """
        return evas.object_image_add()



    def _get_intrinsic_size(self):
        if not self._o or not self._loaded:
            # Image not loaded yet, size not known.
            return 0, 0
        return self._o.image_size_get()


    ########################################################################
    # Properties
    ########################################################################

    def _sync_property_size(self):
        super(Image, self)._sync_property_size()
        size = self.get_computed_inner_size()
        self._o.resize(size)
        self._o.image_fill_set((0, 0), size)
        return SYNC_NEEDS_RENDER


    def _sync_property_image(self):
        return SYNC_NOOP


    def _sync_property_filename(self):
        debug(self["filename"], lf = False)
        self._o.image_file_set(self["filename"])
        err = self._o.image_load_error_get()
        if err:
            raise evas.LoadError, (err, "Unable to load image", self["filename"])

        self._loaded = True
        self._dirty_property("size")
        return SYNC_NEEDS_RENDER


    def _sync_property_pixels(self):
        return SYNC_NOOP

    def _sync_property_data(self):
        return SYNC_NOOP

    def _sync_property_aspect(self):
        return SYNC_NOOP



    ########################################################################
    # Public API
    ########################################################################

    def set_image(self, image_or_file):
        """
        Sets the image to the one provided.  image_or_file can be either a
        filename from which to load the image, or an Imlib2 Image object.
        """

        if isinstance(image_or_file, basestring):
            # Load image from file.
            self["filename"] = image_or_file
            del self["image"], self["pixels"]
        elif imlib2 and isinstance(image_or_file, imlib2.Image):
            # Use Imlib2 image as source for the evas image.
            self["image"] = image_or_file
            #self["image"].signals["changed"].connect_weak(self.set_dirty)
        else:
            raise ValueError, "Unsupported argument to set_image: " + repr(type(image_or_file))

        self._loaded = False


Image._add_properties(('image', 'filename', 'pixels', 'data'), ('aspect', ))



import random

class Container(Object):

    def __init__(self, **kwargs):
        super(Container, self).__init__(**kwargs)

        # Dict holding children (as keys) that have dirty properties that need
        # syncing. 
        self._queued_children = {}
        # A list of our child objects
        self._children = []
        # An evas rectangle object that is drawn using a random color when
        # debug property is True
        self._debug_rect = None
        self._debug_rect_inner = None

        self['debug'] = kwargs.get('debug', False)


    def _canvased(self, canvas):
        """
        Called by our parent container when the top-most ancestor is a Canvas
        object.  As a container we must propagate this call down to our
        children.
        """
        super(Container, self)._canvased(canvas)
        # Notify children of new canvas; this also causes all children
        # properties to be dirtied and sync queued.
        for child in self._children:
            child._canvased(canvas)


    def _uncanvased(self):
        """
        Called by our parent container when we're detached from our current
        canvas.  As a container we must propagate this call down to our
        children.
        """
        super(Container, self)._uncanvased()
        for child in self._children:
            child._uncanvased()


    def _dirty_all_properties(self):
        """
        Declares all properties as dirty on ourselves as well as all our
        children.
        """
        super(Container, self)._dirty_all_properties()
        for child in self._children:
            child._dirty_all_properties()


    def _dirty_property_children(self, prop):
        """
        Dirties the given property for all our children.
        """
        for child in self._children:
            child._dirty_property(prop)


    def _queue_sync(self, child = None):
        """
        Requests from our parent that _sync_dirty_properties be called on the
        next main loop step.  If child is not None, then it means a request
        came from one of our children and we must call its _sync_dirty_properties 
        on next _sync_queued()
        """
        super(Container, self)._queue_sync()

        if child:
            self._queued_children[child] = 1



    def _can_sync_property(self, property):
        # Containers don't actually have an evas object, so we override this
        # method to allow properties to be synced as long as we belong to a
        # canvas.
        return self._canvas != None


    def _get_computed_property_for_child(self, prop, child, default = None):
        """
        Returns the computed property (specified by prop) within the context of
        the child requesting the property (specified by child).  If the
        computed property doesn't exist, return default.  Subclasses of
        Container may wish to return different values depending on the child
        requesting.
        """
        if default is None and prop not in self._computed_properties:
            raise ValueError, "Property '%s' not computed and no default specified" % prop
        if prop == 'extents' and child['passive']:
            prop = 'size-inner'

        value = self._computed_properties.get(prop, default)
        #if prop == 'pos-abs':
        #    return value[0] + 15, value[1] + 15
        return value


    def _sync_dirty_properties(self, debug_prefix=''):
        # XXX: this method is a performance hotspot.
        return_value = 0

        # Fetch the current computed size of the container.   We compare this
        # value to our computed size after we're finished syncing active
        # children.  If the values differ, we propagate SYNC_SIZE_CHANGED
        # up to our parent in the return value.
        size_pre_sync = self._computed_properties.get('size')
        if not size_pre_sync:
            # If 'size' doesn't exist in the _computed_properties dict then it
            # means our size property was dirtied, so we grab 'last-size' which
            # is saved when the property is dirtied.
            size_pre_sync = self._computed_properties.get('last-size', (0, 0))

        # If we have dirty properties of our own, sync them now.
        if len(self._dirty_properties):
            return_value = super(Container, self)._sync_dirty_properties(debug_prefix)
            debug_prefix = debug_prefix + '    '

        assert(not self._is_currently_syncing)
        self._is_currently_syncing = True
    
        # FIXME: maintain separate dicts for passive and active children.
        # Our own properties are synced, now we can sync our children.
        do_passive = False
        for child in self._queued_children.keys():
            # Only do active children in pass 1.
            if child['passive']:
                continue

            result = child._sync_dirty_properties(debug_prefix)
            if not result & SYNC_NOT_FINISHED:
                # Sync of this child is complete, so remove pending resync
                # request.
                del self._queued_children[child]
                child._is_sync_queued = False

            if result & SYNC_SIZE_CHANGED and not do_passive and 'auto' in self['size']:
                # This child's size has changed, so our size may also have changed.
                # FIXME: our size can change if our child's pos also changes;
                # need to check for this.

                # If both our dimensions are specified, child cannot
                # affect our size, so ignore.
                # Otherwise dirty size of all passive children and delete
                # our cached computed size.  (Will be recalculated below.)
                #print "Child %s size changed, force recomputation of our (%s) size" % (child, self)
                if 'size' in self._computed_properties:
                    del self._computed_properties['size']
                for child in self._children:
                    if child['passive']:
                        child._dirty_property('size')
                do_passive = True

            return_value |= result & SYNC_NEEDS_RENDER

        # Recalculate our inner size.  This stores a cached copy in size-inner,
        # which is returned when passive children call _get_extents().  
        # FIXME: this is a bit inelegant.
        self.get_computed_inner_size()

        # Grab our new computed size.  This will return the cached value that
        # got indirectly calculated from the call we just made to compute
        # the inner size, so it's not expensive.
        size_post_sync = self.get_computed_size()
        if size_pre_sync != size_post_sync:
            # Our size changed either due to our own properties or our 
            # children.  Indicate this to our parent.
            return_value |= SYNC_SIZE_CHANGED


        for child in self._queued_children.keys():
            # Only do passive children in pass 2.
            if not child['passive']:
                continue

            result = child._sync_dirty_properties(debug_prefix)
            if not result & SYNC_NOT_FINISHED:
                # Sync of this child is complete, so remove pending resync
                # request.
                del self._queued_children[child]
                child._is_sync_queued = False

            return_value |= result & SYNC_NEEDS_RENDER

        if self["debug"]:
            return_value |= self._update_debug_rect()

        self._is_currently_syncing = False
        return return_value


    def _update_debug_rect(self):
        """
        Updates the debug rectangle for the container based on the container's
        current size.  Assumes debug property is True and therefore _debug_rect
        is created.
        """
        pos = self._computed_properties['pos-abs']
        size = self._get_computed_size()
        pos_inner = self._computed_properties['pos-inner-abs']
        size_inner = self.get_computed_inner_size()
        visible = self._computed_properties['visible-abs']
        if (pos, size) != self._debug_rect.geometry_get() or visible != self._debug_rect.visible_get() or \
           (pos_inner, size_inner) != self._debug_rect_inner.geometry_get():
            #print "SET debug rect %s: pos=%s size=%s" % (self, repr(pos), repr(size))
            self._debug_rect.move(pos)
            self._debug_rect.resize(size)
            self._debug_rect_inner.move(pos_inner)
            self._debug_rect_inner.resize(size_inner)
            if visible:
                self._debug_rect.show()
                self._debug_rect_inner.show()
            else:
                self._debug_rect.hide()
                self._debug_rect_inner.hide()

            return SYNC_NEEDS_RENDER

        return SYNC_NOOP


    def _get_intrinsic_size(self):
        """
        The intrinsic size of a container is based on the computed size of all
        its active children.
        """
        size = [0, 0]
        for child in self._children:
            if child['passive']:
                continue

            child_size = child._get_computed_size()
            child_pos = child.get_computed_position()
            sum = child_pos[0] + child_size[0], child_pos[1] + child_size[1]
            if sum[0] > size[0]:
                size[0] = sum[0]
            if sum[1] > size[1]:
                size[1] = sum[1]

        return tuple(size)



    ########################################################################
    # Properties
    ########################################################################

    def _sync_property_pos(self):
        self._compute_absolute_pos()
        self._dirty_property_children('pos')
        return SYNC_NOOP


    def _sync_property_visible(self):
        # Compute absolute visibility; children will use this value.
        self._compute_absolute_visible()
        self._dirty_property_children('visible')
        return SYNC_NOOP


    def _sync_property_margin(self):
        # Margin affects our position.  If we move, so must our children.  So
        # dirty both our pos and our children's pos.
        self._dirty_property('pos')
        #self._dirty_property_children('pos')
        return SYNC_NOOP


    def _sync_property_padding(self):
        # Padding will affect our inner position, so we must dirty our pos
        # in order to recompute it, which will in turn dirty our children's 
        # pos so they reflow to reflect our new inner pos.
        self._dirty_property('pos')

        size = self['size']
        if 'auto' not in size:
            # Container size is fixed; our inner size changes, so we must
            # update our children's size.  But our own size remains the
            # same (it's fixed after all) so no need to dirty our own size.
            self._dirty_property_children('size')

        elif size == ('auto', 'auto'):
            # If container shrinkwraps in both dimensions, our inner size does
            # not change (it is our intrinsic size) but our border size does
            # change, because it includes the new padding.  Because our inner
            # size remains the same, we don't need to update our children.
            self._dirty_property('size')

        else:
            # This is the case when one dimension is fixed and the other
            # shrinkwraps.  Here both our border size and our inner size 
            # changes, so we must both dirty our own size and our children's
            # size.
            self._dirty_property('size')
            self._dirty_property_children('size')

        return SYNC_NOOP


    def _compute_extents_for_children(self):
        extents = list(self._get_extents())
        for i, val in enumerate(self['size']):
            if val != 'auto':
                extents[i] = self._compute_relative_value(val, extents[i])
        padding = self._get_computed_padding()
        extents[0] -= padding[1] + padding[3]
        extents[1] -= padding[0] + padding[2]

        if self._computed_properties.get('extents') != extents:
            # Extents have changed, our cached padding and margin values
            # need to be recomputed; only relevant if object is not passive,
            # because for passive objects, relative values are not based on
            # extents.
            # FIXME: could be smarter; only need to update active children
            # with a relative size.
            # padding indirectly dirties size
            self._dirty_property_children('padding')
            self._dirty_property_children('margin')
            self._computed_properties['extents'] = extents

        return extents


    def _sync_property_size(self):
        # Compute extents for children, which will dirty the appropriate child
        # properties that depend on our size.
        self._compute_extents_for_children()
        return SYNC_NOOP


    def _sync_property_opacity(self):
        self._compute_absolute_opacity()
        self._dirty_property_children('opacity')
        return SYNC_NOOP


    def _sync_property_color(self):
        self._compute_absolute_color()
        self._dirty_property_children('color')
        return SYNC_NOOP


    def _sync_property_debug(self):
        if self["debug"]:
            if not self._debug_rect:
                colors = [ random.randint(0, 255) for x in range(3) ]
                self._debug_rect = self.get_canvas().get_evas().object_rectangle_add()
                self._debug_rect.color_set(*(colors + [50]))
                self._debug_rect_inner = self.get_canvas().get_evas().object_rectangle_add()
                self._debug_rect_inner.color_set(*(colors + [50]))

            return SYNC_NEEDS_RENDER

        elif not self["debug"] and self._debug_rect:
            self._debug_rect.hide()
            return SYNC_NEEDS_RENDER

        return SYNC_NOOP



    ########################################################################
    # Public API
    ########################################################################

    def add_child(self, child):
        if child._parent:
            raise CanvasError, "Attempt to parent an adopted child."

        self._children.append(child)
        child._adopted(self)
        if self.get_canvas():
            child._canvased(self.get_canvas())

Container._add_properties(append = ('debug',))


import kaa, kaa.evas

class Canvas(Container):
    def __init__(self, **kwargs):
        super(Canvas, self).__init__(**kwargs)
        self._names = {}
        self._render_needed = False


    def _wrap(self, evas_object):
        super(Canvas, self)._wrap(evas_object)
        kaa.signals["step"].connect_weak(self._sync_queued)


    def _sync_dirty_properties(self, debug_prefix=''):
        result = super(Canvas, self)._sync_dirty_properties(debug_prefix)
        if result & SYNC_NEEDS_RENDER:
            self._render_needed = True



    def _sync_queued(self):
        if len(self._dirty_properties) == len(self._queued_children) == 0:
            return
        kaa.evas.benchmark_reset()
        t0=time.time()
        self._sync_dirty_properties()
        t1=time.time()
        if self._render_needed:
            self._render()
            self._render_needed = False

        t2=time.time()

        sync=t1-t0
        render=(t2-t1) - _bench_subtract
        all=(t2-t0) - _bench_subtract

        evas=kaa.evas.benchmark_get()
        print " @ Canvas sync=%.05f (%.2f%%), render=%.5f (%.2f%%); all=%.05f evas=%f;\n   OVERHEAD=%.05f (%.2f%%)" % \
            (sync, sync/all*100, render, render/all*100, all, evas, all-evas, (all-evas)/all*100)


    def _can_sync_property(self, property):
        return Object._can_sync_property(self, property)


    def _set_property_size(self, dummy, size):
        if size != ('auto', 'auto'):
            output_size = self._o.output_size_get()
            if size != output_size:
                raise ValueError, "Canvas with size %s cannot be resized to %s" % (output_size, size)

            self._computed_properties['size'] = size
        return size


    def _sync_property_pos(self):
        padding = self._get_computed_padding()
        self._computed_properties['pos-abs'] = padding[3], padding[0]
        self._computed_properties['pos-inner-abs'] = padding[3], padding[0]
        self._dirty_property_children('pos')
        return SYNC_NOOP


    def _sync_property_visible(self):
        self._computed_properties['visible-abs'] = self['visible']
        self._dirty_property_children('visible')
        return SYNC_NOOP


    def _sync_property_opacity(self):
        self._computed_properties['opacity-abs'] = self['opacity']
        return SYNC_NOOP

    def _sync_property_color(self):
        self._computed_properties['color-abs'] = self['color']
        return SYNC_NOOP


    def _render(self):
        return self._o.render()


    def _register_object_name(self, name, object):
        self._names[name] = weakref(object)


    def _unregister_object_name(self, name):
        if name in self._names:
            del self._names[name]


    def _get_extents(self):
        return self['size']

    def _get_computed_size(self):
        return self['size']

    def get_computed_size(self):
        return self['size']

    def get_evas(self):
        return None


    def get_canvas(self):
        return self




from kaa import display

class X11Canvas(Canvas):
    def __init__(self, size, use_gl = None, title = "Canvas", **kwargs):
        self._window = display.X11Window(size = size, title = title)

        if use_gl == None:
            use_gl = "gl_x11" in evas.render_method_list() and \
                     self._window.get_display().glx_supported()

        self._canvas_window = display.EvasX11Window(use_gl, size = size, parent = self._window)
        self._canvas_window.show()

        super(X11Canvas, self).__init__(**kwargs)

        self._wrap(self._canvas_window.get_evas()._evas)
        self._canvas_window.set_cursor_hide_timeout(1)

        self["size"] = size


    def _set_property_visible(self, dummy, visible):
        self._visibility_on_next_render = visible
        return visible


    def _render(self):
        if not self._visibility_on_next_render:
            self._window.hide()
        regions = self._o.render()
        if self._visibility_on_next_render:
            # XXX: this kludge is used to subtract X11 mapping time from the
            # render time, so as not to inflate overhead calculation.  Remove
            # this eventually.
            t0=time.time()
            self._window.show()
            global _bench_subtract
            _bench_subtract = 0#time.time()-t0
        return regions

    def get_evas(self):
        return self._o
