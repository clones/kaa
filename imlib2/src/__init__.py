# -*- coding: iso-8859-1 -*-
# -----------------------------------------------------------------------------
# Imlib2.py - Imlib2 wrapper for Python
# -----------------------------------------------------------------------------
# $Id$
# -----------------------------------------------------------------------------
# kaa.imlib2 - An imlib2 wrapper for Python
# Copyright (C) 2004-2006 Dirk Meyer, Jason Tackaberry
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

import types
import math
import os
import glob
import md5

from version import VERSION

# imlib2 wrapper
import _Imlib2

# image and font wrapper
from image import *
from font import *

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

def open_without_cache(file):
    """
    Create a new image object from the file 'file' without using the
    internal cache.
    """
    return Image(file, False)


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


def new(size, bytes = None, from_format = "BGRA", copy = True):
    """
    Generates a new Image of size 'size', which is a tuple holding the width
    and height.  If 'bytes' is specified, the image is initialized from the
    raw BGRA data.  If 'copy' is False, 'bytes' must be either a write buffer
    or an integer pointing to a location in memory that will be used to hold
    the image.  (In this caes, from_format must be BGRA.)
    """
    if 0 in size:
        raise ValueError, "Invalid image size %s" % repr(size)
    for val in size:
        if not isinstance(val, int):
            raise ValueError, "Invalid image size %s" % repr(size)
    if bytes:
        if False in map(lambda x: x in "RGBA", list(from_format)):
            raise ValueError, "Converting from unsupported format: " +  from_format
        if type(bytes) != int and len(bytes) < size[0]*size[1]*len(from_format):
            raise ValueError, "Not enough bytes for converted format: expected %d, got %d" % \
                              (size[0]*size[1]*len(from_format), len(bytes))
        return Image(_Imlib2.create(size, bytes, from_format, copy))
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


def get_font_style_geometry(style):
    """
    Return the additional pixel the font needs for the style. This function
    will return left, top, right, bottom as number of pixels the text will
    start to the left/top and the number of pixels it needs more at the
    right/bottom. To avoid extra calculations the function will also return
    the additional width and height needed for the style.
    """
    return TEXT_STYLE_GEOMETRY[style]
