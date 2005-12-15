__all__ = [ 'Image' ]

from object import *
import types, os, re
from kaa import evas
try:
    from kaa import imlib2
except ImportError:
    imlib2 = None


class Image(Object):

    PIXEL_FORMAT_NONE = 0
    PIXEL_FORMAT_ARGB32 = 1
    PIXEL_FORMAT_YUV420P_601 = 2

    def __init__(self, image_or_file = None):
        super(Image, self).__init__()

        # Remove previous "size" property -- we want size property to sync
        # _after_ the image gets loaded (via image, filename, or pixels
        # properties).  And since pos can depend on size, we move pos
        # property as well.  And since clip depends on pos, same thing. :)
        for prop in ("size", "pos", "clip"):
            self._supported_sync_properties.remove(prop)
        self._supported_sync_properties += ["image", "filename", "pixels", "data", "dirty", 
                                            "size", "pos", "clip", "has_alpha", "border"]

        self._loaded = False
        self["has_alpha"] = True

        if image_or_file:
            self.set_image(image_or_file)


    def _reset(self):
        super(Image, self)._reset()
        self._loaded = False


    def _get_aspect_ratio(self):
        orig = self.get_image_size()
        aspect = orig[0] / float(orig[1])
        return aspect
     
        
    def _compute_size(self, parent_val, val):
        val = list(super(Image, self)._compute_size(parent_val, val))
        aspect = self._get_aspect_ratio()
        orig = self.get_image_size()
        for index in range(2):
            if val[index] == 0:
                val[index] = orig[index]
            elif val[index] == -1:
                if index == 0:
                    val[index] = int(val[1] * aspect)
                else:
                    val[index] = int(val[0] / aspect)

        return tuple(val)



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
        super(Image, self)._canvased(canvas)

        if not self._o and canvas.get_evas():
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
        self._notify_parent_property_changed("size")
        self._loaded = True

    def _sync_property_filename(self):
        if self._loaded:
            return

        self._o.file_set(self["filename"])
        err = self._o.load_error_get()
        if err:
            raise evas.LoadError, (err, "Unable to load image", self["filename"])

        if self["size"] == ("auto", "auto"):
            size = self._o.size_get()
        else:
            size = self._get_computed_size()
        self._o.resize(size)
        self._o.fill_set((0, 0), size)

        self._notify_parent_property_changed("size")
        self._loaded = True

    def _sync_property_pixels(self):
        if self._loaded:
            return

        data, w, h, format = self["pixels"]
        old_size = self._o.geometry_get()[1]
        self._o.size_set((w, h))
        self._o.pixels_import(data, w, h, format)

        if self["size"] == ("auto", "auto"):
            size = w, h
        else:
            size = self._get_computed_size()

        self._o.pixels_dirty_set()
        self._o.resize(size)
        self._o.fill_set((0, 0), size)

        if size != old_size:
            # Only need to reflow if target size has changed.
            self._notify_parent_property_changed("size")

        self._loaded = True

    def _sync_property_data(self):
        if self._loaded:
            return

        data, copy = self["data"]
        self._o.data_set(data, copy)
        self._loaded = True

    def _sync_property_pos(self):
        # For images, delay computing pos until we have an image loaded,
        # since position could depend on size, and we don't know size until
        # we're loaded.
        if not self._loaded:
            return False
        return super(Image, self)._sync_property_pos()


    def _sync_property_size(self):
        # If the image isn't loaded, we won't know how to calculate the size
        # if 0 or -1 are given for image size.
        if not self._loaded:
            return False

        # Calculates size and resizes the object.
        super(Image, self)._sync_property_size()
        self._o.fill_set((0, 0), self._o.geometry_get()[1])
        #self.get_size())
    
    def _sync_property_has_alpha(self):
        self._o.alpha_set(self["has_alpha"])
    
    def _sync_property_dirty(self):
        if not self["dirty"]:
            return

        self._o.pixels_dirty_set()

        # We need to call this function explicitly for canvas backends where
        # this data gets copied again (like GL textures).
        self._o.data_set(self._o.data_get(), copy = False)

        self["dirty"] = False


    def _sync_property_border(self):
        self._o.border_set(*self["border"])

    def _get_actual_size(self):
        if not self._loaded:
            # At this point we actually are loaded, but self._loaded hasn't
            # been set to True yet.  We'll be called here for size dimensions
            # set to "auto" in which case we want to return the actual image
            # size.
            return self.get_image_size()
        return super(Image, self)._get_actual_size()

    #
    # Public API
    #

    def set_dirty(self, dirty = True):
        self["dirty"] = dirty

    def import_pixels(self, data, w, h, format):
        del self["filename"], self["image"], self["pixels"], self["data"]
        self._loaded = False
        self["pixels"] = (data, w, h, format)

    def set_data(self, data, copy = False):
        del self["filename"], self["image"], self["pixels"], self["data"]
        self._loaded = False
        self["data"] = (data, copy)

    def as_image(self):
        if not imlib2:
            assert CanvasError, "kaa.imlib2 not available."

        if not self["image"]:
            # No existing Imlib2 image, so we need to make one.
            if self._loaded:
                # The evas object already exists, so create a new Imlib2 image
                # from the evas data and tell evas to use that buffer for the
                # image instead.
                size = self._o.size_get()
                self["image"] = imlib2.new(size, self._o.data_get(), copy = True)
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

    def set_border(self, left, right, top, bottom):
        self["border"] = (left, right, top, bottom)

    def get_border(self):
        return self["border"]
