# -*- coding: iso-8859-1 -*-
# -----------------------------------------------------------------------------
# $Id$
# -----------------------------------------------------------------------------
# kaa.canvas - Canvas library based on kaa.evas
# Copyright (C) 2005, 2006 Jason Tackaberry
#
# First Edition: Jason Tackaberry <tack@sault.org>
# Maintainer:    Jason Tackaberry <tack@sault.org>
#
# Please see the file AUTHORS for a complete list of authors.
#
# This library is free software; you can redistribute it and/or modify
# it under the terms of the GNU Lesser General Public License version
# 2.1 as published by the Free Software Foundation.
#
# This library is distributed in the hope that it will be useful, but
# WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
# Lesser General Public License for more details.
#
# You should have received a copy of the GNU Lesser General Public
# License along with this library; if not, write to the Free Software
# Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA
# 02110-1301 USA
#
# -----------------------------------------------------------------------------

__all__ = [ 'Image' ]

from object import *
import types, os, re
import kaa
from kaa import evas

try:
    from kaa import imlib2
except ImportError:
    imlib2 = None

try:
    from kaa.canvas import _svg
except ImportError:
    _svg = None

try:
    from kaa.canvas import _mng
except ImportError:
    _mng = None

MNG_MAGIC = "\x8aMNG\x0d\x0a\x1a\x0a"


# SOME DOC ABOUT ASPECT
#
# If aspect is a value, keep this aspect. If width and height are given,
# fit into the given width and keep the aspect. If only one is provided,
# calculate the other based on the aspect.
#
# If aspect is 'preserve' use the aspect of the image file and act as if
# a value is given.
#
# If aspect is 'ignore' use the given width and height, scretch image if needed.
# If one or both attributes are missing, take the width or height from the image
#
# If aspect is 'auto' preserve the image aspect if only one of width or height
# is given (== 'preserve'). If both are given, use this ignoring the aspect
# (== 'ignore'). This is the default aspect.

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

        self._supported_sync_properties += [
            "border", "image", "filename", "pixels", "data", "dirty",
            "aspect", "size", "pos", "clip", "has_alpha"
        ]

        self._loaded = False
        self["has_alpha"] = True
        self["dirty"] = False
        self["aspect"] = "auto"

        # For animated images
        self._mng = None
        self._update_frame_timer = kaa.WeakTimer(self._update_frame)

        if image_or_file:
            self.set_image(image_or_file)


    def __repr__(self):
        s = "<canvas.%s " % self.__class__.__name__
        if self["filename"]:
            s += "file=\"%s\" " % self["filename"]
        elif self["pixels"]:
            s += "imported "
        elif self["data"]:
            s += "custom "
        s += "size=%s " % str(self["size"])
        if self._o:
            s += "asize=%s imgsize=%s" % (str(self._o.geometry_get()[1]), str(self._o.size_get()))
        return s + ">"



    def _reset(self):
        super(Image, self)._reset()
        self._loaded = False


    def _get_aspect_ratio(self):
        orig = self.get_image_size()
        if orig[1] == 0:
            return 1.0

        return orig[0] / float(orig[1])
 
    def _get_minimum_size(self):
        image_size = list(self.get_image_size())
        size = self._apply_aspect_to_size(list(self["size"]))
        # If either dimension is fixed (i.e. not a percentage) then our min
        # size must reflect that.
        if isinstance(size[0], int):
            image_size[0] = size[0]
        if isinstance(size[1], int):
            image_size[1] = size[1]
        return image_size
        
    def _compute_size(self, size, child_asking, extents = None):
        if "auto" in size:
            # Object._compute_size will replace "auto" with the object's
            # container's geometry.  For images, "auto" means the image's native
            # size, so we replace "auto" here, before passing the size to
            # Object._compute_size.
            image_size = self.get_image_size()
            size = list(size)
            for i in range(2):
                if size[i] == "auto":
                    size[i] = image_size[i]

        size = list(super(Image, self)._compute_size(size, child_asking, extents))
        size = self._apply_aspect_to_size(size)
        #print "IMAGE size", self, size, child_asking
        return size

    def _get_computed_pos(self, child_asking = None, with_margin = True):
        pos = list(super(Image, self)._get_computed_pos(child_asking, with_margin))
        # The image will be scaled down to compensate for any padding, so here
        # we adjust the position of the image to account for the padding.
        padding = self._get_computed_padding()
        pos[0] += padding[3]
        pos[1] += padding[0]
        return pos


    def _apply_aspect_to_size(self, size):
        if self["aspect"] not in ("ignore", "preserve", "auto"):
            aspect = self["aspect"]
        else:
            aspect = self._get_aspect_ratio()

        if size[0] == size[1] == -1 and self._loaded:
            return self.get_image_size()
        
        for index in range(2):
            if size[index] == -1:
                if self["aspect"] == "ignore":
                    # for ignore we use the image values
                    size[index] = self.get_image_size()[index]
                    
                # We can only keep aspect if the other dimension is known.
                # (float value, preserve or auto)
                elif isinstance(size[1-index], int) and size[1-index] != -1:
                    if index == 0:
                        size[index] = int(size[1] * aspect)
                    else:
                        size[index] = int(size[0] / aspect)
                        
        # if both values or not -1 and we are not in ignore or auto,
        # set width and height to aspect and fit it!
        if not self["aspect"] in ("ignore", "auto") and isinstance(size[0], int) \
               and size[0] != -1 and isinstance(size[1], int) and size[1] != -1:
            width, height = self.get_image_size()
            if int(size[0] / aspect) < size[1]:
                size[1] = int(size[0] / aspect)
            elif int(size[1] * aspect) < size[0]:
                size[0] = int(size[1] * aspect)
        return size


    def _canvased(self, canvas):
        super(Image, self)._canvased(canvas)

        if not self._o and canvas.get_evas():
            o = canvas.get_evas().object_image_add()
            self._wrap(o)

    def _can_sync_property(self, prop):
        if self._loaded and prop in ("image", "filename", "pixels", "data"):
            return False

        # Don't sync position until an image is loaded, since position could 
        # depend on our size (center, bottom); don't sync size until loaded 
        # because size could require image size for aspect ratio.
        if not self._loaded and prop in ("pos", "size"):
            return False

        return super(Image, self)._can_sync_property(prop)


    def _set_property_filename(self, filename):
        assert(isinstance(filename, str))
        self._set_property_generic("filename", filename)


    def _set_property_image(self, image):
        assert(imlib2 and isinstance(image, imlib2.Image))
        self._set_property_generic("image", image)

    def _set_property_aspect(self, aspect):
        if isinstance(aspect, str) and aspect.replace(".", "").isdigit():
            aspect = float(aspect)

        if aspect not in ("preserve", "ignore", "auto") and \
               not isinstance(aspect, (int, float)):
            raise ValueError, "Aspect property must be 'preserve', 'ignore', 'aspect' or numeric."

        self._force_sync_property("size")
        self._set_property_generic("aspect", aspect)

    def _sync_image_common(self, old_size):
        # Computed size may depend on new image size, so dirty cached size.
        self._dirty_cached_value("size")
        size = self._get_computed_inner_size()
        self._o.resize(size)
        self._o.fill_set((0, 0), size)
        # We've already calculated and updated the size, so there's no need to
        # sync size property again if it is scheduled for syncing.
        self._remove_sync_property("size")

        self._loaded = True

        if old_size != size:
            # Only need to reflow if target size has changed.
            self._request_reflow("size", old_size, size)



    def _sync_property_image(self):
        old_size = self._o.geometry_get()[1]
        size = self["image"].size
        self._o.size_set(size)
        self._o.data_set(self["image"].get_raw_data(), copy = False)
        self._sync_image_common(old_size)


    def _sync_property_filename(self):
        self._mng = None
        ext = os.path.splitext(self["filename"])[1]
        if ext.lower() == ".svg":
            if not _svg:
                raise ValueError, "SVG support has not been enabled"
            bytes = file(self["filename"]).read()
            if bytes.find("<svg") == -1:
                raise ValueError, "'%s' is not a valid SVG" % self["filename"]

            # Compute size, but bypass the aspect calculations, since we 
            # don't know the image's native size yet.  Substitute "auto"
            # in the size property for -1 for loading the SVG.
            size = [ (x, -1)[x == "auto"] for x in self["size"] ]
            w, h = super(Image, self)._compute_size(size, None, None)
            # Render the SVG to a buffer, returning actual size.
            w, h, buf = _svg.render_svg_to_buffer(w, h, bytes)
            self["data"] = w, h, buf, False
            return

        elif ext.lower() == ".mng":
            bytes = file(self["filename"]).read()
            if bytes[:len(MNG_MAGIC)] != MNG_MAGIC:
                raise ValueError, "File '%s' is not a MNG file" % file

            if not _mng:
                raise ValueError, "MNG support has not been enabled"

            self._mng = _mng.MNG(kaa.WeakCallback(self._mng_refresh))
            width, height, delay, buffer = self._mng.open(bytes)
            self["data"] = width, height, buffer, False
            return


        old_size = self._o.geometry_get()[1]
        self._o.file_set(self["filename"])
        err = self._o.load_error_get()
        if err:
            raise evas.LoadError, (err, "Unable to load image", self["filename"])

        self._sync_image_common(old_size)


    def _sync_property_pixels(self):
        old_size = self._o.geometry_get()[1]
        data, w, h, format = self["pixels"]
        self._o.size_set((w, h))
        self._o.pixels_import(data, w, h, format)
        self._o.pixels_dirty_set()

        self._sync_image_common(old_size)


    def _sync_property_data(self):
        old_size = self._o.geometry_get()[1]
        width, height, data, copy = self["data"]
        self._o.size_set((width, height))
        self._o.data_set(data, copy)

        self._sync_image_common(old_size)

        self._update_frame()


    def _sync_property_size(self):
        # Calculates size and resizes the object.
        super(Image, self)._sync_property_size()
        self._o.fill_set((0, 0), self._o.geometry_get()[1])
    
    
    def _sync_property_has_alpha(self):
        self._o.alpha_set(self["has_alpha"])
    
    
    def _sync_property_dirty(self):
        if not self["dirty"]:
            return

        if isinstance(self["dirty"], (tuple, list)):
            for (x, y, w, h) in self["dirty"]:
                self._o.data_update_add(x, y, w, h)
        else:
            self._o.pixels_dirty_set()

        # We need to call this function explicitly for canvas backends where
        # this data gets copied again (like GL textures).  It's essentially a
        # bug in evas.
        #self._o.data_set(self._o.data_get(), copy = False)
        self["dirty"] = False


    def _sync_property_border(self):
        self._o.border_set(*self["border"])

    def _sync_property_aspect(self):
        return True



    # For animation


    def _mng_refresh(self, x, y, w, h):
        self.set_dirty((x, y, w, h))


    def _mng_update(self):
        delay = self._mng.update()
        while delay == 1:
            delay = self._mng.update()

        if delay == 0:
            self._update_frame_timer.stop()
            return

        delay /= 1000.0
        cur_interval = self._update_frame_timer.interval
        if cur_interval and abs(delay - cur_interval) > 0.02 or \
           not self._update_frame_timer.active():
            self._update_frame_timer.start(delay)

    def _update_frame(self):
        if self._mng:
            self._mng_update()
        else:
            self._update_frame_timer.stop()


    #
    # Public API
    #

    def resize(self, width = None, height = None):
        if self["aspect"] not in ("ignore", "auto") and \
               (height == None or width == None):
            # We're preserving an aspect and only one dimension
            # has been specified, set the other one to -1, which will cause
            # _compute_size() to compute that dimension based on the aspect.
            if width != None:
                height = -1
            elif height != None:
                width = -1

        super(Image, self).resize(width, height)

        if self._loaded and self["filename"] and \
           os.path.splitext(self["filename"])[1].lower() == ".svg":
            # If file is a SVG and the requested size is more than two times
            # (in area) greater than the image's native size, rerender the SVG
            # at the new size.  (XXX: the 2X factor could use some empirical 
            # testing, or perhaps we should reload on all upscaling?  Or 
            # never?)
            actual = self.get_image_size()
            size = self._get_computed_inner_size()
            if float(size[0]*size[1]) / (actual[0]*actual[1]) > 2.0:
                self._loaded = False
                self._force_sync_property("filename")


    def set_image(self, image_or_file):
        del self["filename"], self["image"], self["pixels"]
        if isinstance(image_or_file, basestring):
            self["filename"] = image_or_file
        elif imlib2 and isinstance(image_or_file, imlib2.Image):
            self["image"] = image_or_file
            # Use weakref connection because we already hold a ref to the
            # image: avoids cycle.
            self["image"].signals["changed"].connect_weak(self.set_dirty)
        else:
            raise ValueError, "Unsupported argument to set_image: " + repr(type(image_or_file))

        self._loaded = False


    def set_dirty(self, region = True):
        if self["dirty"] == True:
            # Entire region is already dirty.
            return

        if region == True:
            # Region can be True, which indicates the entire image needs
            # updating.
            self["dirty"] = True
            return

        # Otherwise it should be a sequence (x, y, w, h)
        assert(isinstance(region, (list, tuple)) and len(region) == 4)
        if not isinstance(self["dirty"], list):
            self["dirty"] = [region]
        else:
            self["dirty"] = self["dirty"] + [region]


    def import_pixels(self, data, w, h, format):
        del self["filename"], self["image"], self["pixels"], self["data"]
        self._loaded = False
        self["pixels"] = (data, w, h, format)


    def set_data(self, width, height, data, copy = False):
        del self["filename"], self["image"], self["pixels"], self["data"]
        self._loaded = False
        self["data"] = (width, height, data, copy)


    def as_image(self):
        if not imlib2:
            assert CanvasError, "kaa.imlib2 not available."

        if not self["image"]:
            # No existing Imlib2 image, so we need to make one.
            if (self["filename"] and self._loaded) or (not self["filename"] and self._o):
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

    def set_aspect(self, aspect):
        self["aspect"] = aspect

    def get_aspect(self):
        return self["aspect"]


    # These public methods only apply to animated images

    def stop(self):
        self._update_frame_timer.stop()

    def start(self):
        self._update_frame()

    def is_playing(self):
        return self._update_frame_timer.active()

