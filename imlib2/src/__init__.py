# -*- coding: iso-8859-1 -*-
# -----------------------------------------------------------------------------
# Imlib2.py - Imlib2 wrapper for Python
# -----------------------------------------------------------------------------
# $Id$
# -----------------------------------------------------------------------------
# Copyright (C) 2004-2005 Jason Tackaberry <tack@sault.org>
#
# Maintainers: Jason Tackaberry <tack@sault.org>
#              Dirk Meyer <dmeyer@tzi.de>
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful, but
# WITHOUT ANY WARRANTY; without even the implied warranty of MER-
# CHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the GNU General
# Public License for more details.
#
# You should have received a copy of the GNU General Public License along
# with this program; if not, write to the Free Software Foundation, Inc.,
# 59 Temple Place, Suite 330, Boston, MA 02111-1307 USA
#
# -----------------------------------------------------------------------------

import types
import math
import os
import glob
import md5

# imlib2 wrapper
import _Imlib2

# image and font wrapper
from image import *
from font import *

class Display(object):
    """
    Although not part of Imlib2, this class is here as a convenience, and
    provides very basic X11 display support.

    Instances may have attributes 'expose_callback' and 'input_callback' set,
    and when the window receives an Expose or KeyPress event, the respective
    callbacks will be invoked.  If a backing store is set for the display,
    expose events will be handled and the damaged regions redrawn.  If an
    application requires something more elaborate, it will have to set its
    own 'expose_callback'.  These callbacks are in the form:

        expose_callback(regions_list)
            - where regions_list is a list of tuples, where each tuple is in
              the form ((x, y), (width, height)).

        input_callback(keycode)
            - where keycode is the X key code of the key that was pressed.

    """
    def __init__(self, (w, h), dither = True, blend = False,
                 backing_store = None):
        """
        Create a new window of width 'w' and height 'h' on the current X11
        display (as specified in the DISPLAY environment variable).  If
        'dither' is True, images will be dithered to use the depth of the
        display (looks much better at the expense of performance).  If
        'blend' is True, all images being rendered to the window will be
        alpha-blended.  Both 'dither' and 'blend' options can be overridden
        on a per-image basis when calling Display.render().

        'backing_store' is an Image object that will be used for handling 
        expose events.  Damaged regions of the window will be redrawn from
        this Image.  If 'backing_store' is True, rather than an Image object,
        a new image will be automatically created for this purpose.
        """
        self.__dict__[ '_display' ] = _Imlib2.new_display(w, h)
        self.size = (w, h)
        self.width = w
        self.height = h
        self.blend = blend
        self.dither = dither
        self.set_cursor_hide_timeout(-1)
        self.set_backing_store(backing_store)


    def set_cursor_hide_timeout(self, timeout):
        """
        Hides mouse cursor after the specified timeout in seconds after no
        motion has occured.  A value of 0 makes the cursor permanently
        hidden, and -1 is permanently visible.)
        """
        self.cursor_timeout = timeout

    def set_backing_store(self, img):
        if img == True:
            img = new( (self.width, self.height) )
        self.backing_store = img
        if not self.expose_callback and img:
            self.expose_callback = self._handle_expose_default

    def _handle_expose_default(self, regions):
        if not self.backing_store:
            return

        for (pos, size) in regions:
            self._display.render(self.backing_store._image, pos, pos, size,
				    self.dither, self.blend)
        

    def render(self, image, dst_pos = (0, 0), src_pos = (0, 0),
               src_size = (-1, -1), dither = None, blend = None):
        """
        Renders the given image to the Window at the coordinates specified
        by 'dst_pos'.  The image will be offset by coordinates 'src_pos'.
        'src_size' specifies the target size of the rendered image.  A value
        of -1 for a dimension will use the image's original size for that
        dimension.  'dither' and 'blend' specifies whether the image will be
        dithered to the windows display depth, or alpha-blended onto the 
        display.  Both options will decrease performance at the expense of
        quality.  (However, if the image has no alpha channel, setting 'blend'
        has no effect.)  If neither of these options are specied, it will use
        the values that were passed to the constructor.
        """
        if blend == None:
            blend = self.blend
        if dither == None:
            dither = self.dither

        if not isinstance(image, Image):
            raise ValueError, image
        if self.backing_store and self.backing_store != image:
            self.backing_store.blend(image, src_pos, src_size, dst_pos, 
                                     merge_alpha = not blend)
        return self._display.render(image._image, dst_pos, src_pos, src_size,
				    dither, blend)

    def handle_events(self):
        """
        Handles pending X11 events.  Call this function regularly from within
        your mainloop.

        Returns: True if an event was handled, or False otherwise.
        """
        return self._display.handle_events(self.cursor_timeout)


    def __setattr__( self, key, value ):
        if key in ( 'input_callback', 'expose_callback' ):
            return setattr( self.__dict__[ '_display' ],
                    key, value )
        else:
            self.__dict__[ key ] = value

    def __getattr__( self, key ):
        if key in ( 'input_callback', 'expose_callback', 'socket' ):
            return getattr( self.__dict__[ '_display' ], key )
        else:
            return self.__dict__[ key ]


# Implement a crude image cache.
#
# Imlib2 maintains its own cache, but I don't think it caches
# the raw image data, since this ends up being faster.

_image_cache = {
    "images": {},
    "order": [],
    "size": 0,
    "max-size": 16*1024   # 16 MB
}

def open(file):
    """
    Create a new image object from the file 'file'.
    """
    if file in _image_cache["images"]:
        return _image_cache["images"][file].copy()

    image = Image(file)
    _image_cache["images"][file] = image
    _image_cache["order"].insert(0, file)
    _image_cache["size"] += image.width * image.height * 4 / 1024

    while _image_cache["size"] > _image_cache["max-size"]:
        file = _image_cache["order"].pop()
        expired = _image_cache["images"][file]
        del _image_cache["images"][file]
        _image_cache["size"] -= expired.width * expired.height * 4 / 1024

    return image


def open_from_memory(buf):
    """
    Create a new image object from a memory buffer.
    """
    if type(buf) == str:
        buf = buffer(buf)
    img = _Imlib2.open_from_memory(buf)
    return Image(img)


def new(size, bytes = None, from_format = "BGRA"):
    """
    Generates a new Image of size 'size', which is a tuple holding the width
    and height.  If 'bytes' is specified, the image is initialized from the
    raw BGRA data.
    """
    if 0 in size:
        raise ValueError, "Invalid image size %s" % repr(size)
    for val in size:
        if not isinstance(val, int):
            raise ValueError, "Invalid image size %s" % repr(size)
    if bytes:
        if False in map(lambda x: x in "RGBA", list(from_format)):
            raise ValueError, "Converting from unsupported format: " + \
		  from_format
        if len(bytes) < size[0]*size[1]*len(from_format):
            raise ValueError, "Not enough bytes for converted format: " + \
		  "expected %d, got %d" % (size[0]*size[1]*len(from_format),
					   len(bytes))
        return Image(_Imlib2.create(size, bytes, from_format))
    else:
        return Image(_Imlib2.create(size))


def add_font_path(path):
    """
    Add the given path to the list of paths to scan when loading fonts.
    """
    _Imlib2.add_font_path(path)


def load_font(font, size):
    """
    Return a Font object from the given font specified in the form
    'FontName/Size', such as 'Arial/16'
    """
    return Font(font + "/" + str(size))
