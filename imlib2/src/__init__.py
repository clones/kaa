# -*- coding: iso-8859-1 -*-
# -----------------------------------------------------------------------------
# Imlib2.py - Imlib2 wrapper for Python
# -----------------------------------------------------------------------------
# $Id$
# -----------------------------------------------------------------------------
# kaa.imlib2 - An imlib2 wrapper for Python
# Copyright (C) 2004-2006 Dirk Meyer, Jason Tackaberry
#
# First Edition: Jason Tackaberry <tack@urandom.ca>
# Maintainer:    Jason Tackaberry <tack@urandom.ca>
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
    'images': {},
    'order': [],
    'size': 0,
    'max-size': 16*1024   # 16 MB
}

def open_without_cache(filename):
    """
    Decode an image from disk without using the internal cache.

    :param filename: path to the file to open
    :type filename: str
    :returns: :class:`~imlib2.Image` object
    """
    return Image(filename, False)


def open(filename):
    """
    Decode an image from disk.

    :param filename: path to the file to open
    :type filename: str
    :returns: :class:`~imlib2.Image` object

    This function will cache the raw image data of the loaded file, so that
    subsequent invocations with the given filename will load from cache.

    .. note::
       The cache is currently fixed at 16MB and cannot yet be managed through
       a public API.
    """
    if filename in _image_cache['images']:
        return _image_cache['images'][filename].copy()

    image = Image(filename)
    _image_cache['images'][filename] = image
    _image_cache['order'].insert(0, filename)
    _image_cache['size'] += image.width * image.height * 4 / 1024

    while _image_cache['size'] > _image_cache['max-size']:
        filename = _image_cache['order'].pop()
        expired = _image_cache['images'][filename]
        del _image_cache['images'][filename]
        _image_cache['size'] -= expired.width * expired.height * 4 / 1024

    return image


def open_from_memory(buf):
    """
    Decode an image stored in memory.

    :param buf: encoded image data
    :type buf: str or buffer
    :returns: :class:`~imlib2.Image` object
    """
    if type(buf) == str:
        buf = buffer(buf)
    img = _Imlib2.open_from_memory(buf)
    return Image(img)


def open_svg_from_memory(data, size=None):
    """
    Render an SVG image stored in memory.

    :param data: the XML data specifying the SVG
    :type data: str
    :param size: specifies the width and height of the rasterized image; if
                 None, the size is taken from the SVG itself (if given).
    :type size: 2-tuple of ints or None
    :returns: :class:`~imlib2.Image` object
    """
    if not size:
        size = 0,0
    w, h, buf = _Imlib2.render_svg_to_buffer(size[0], size[1], data)
    return new((w,h), buf, from_format = 'BGRA', copy = True)


def open_svg(filename, size=None):
    """
    Render an SVG image from disk.

    :param filename: path to the SVG file to open
    :type filename: str
    :param size: specifies the width and height of the rasterized image; if
                 None, the size is taken from the SVG itself (if given).
    :type size: 2-tuple of ints or None
    :returns: :class:`~imlib2.Image` object
    """
    return open_svg_from_memory(file(filename).read(), size)


def new(size, bytes=None, from_format='BGRA', copy=True):
    """
    Create a new Image object (optionally) from existing raw data.

    :param size: width and height of the image to create
    :type size: 2-tuple of ints
    :param bytes: raw image data from which to initialize the image; if an int,
                  specifies a pointer to a location in memory holding the raw
                  image (default: None)
    :type bytes: str, buffer, int, None
    :param from_format: specifies the pixel format of the supplied raw data;
                        can be any permutation of RGB or RGBA.  (default: BGRA,
                        which is Imlib2's native pixel format).
    :type from_format: str
    :param copy: if True, the raw data ``bytes`` will be copied to the Imlib2
                 object; if False, ``bytes`` must be either a writable buffer
                 or an integer pointing to a location in memory (in which case,
                 from_format must be 'BGRA')
    :type copy: bool
    :returns: :class:`~imlib2.Image` object

    ``bytes`` can be an integer, acting as a pointer to memory, which is useful
    with interoperating with other libraries, however this should be used with
    extreme care as incorrect values can segfault the interpeter.
    """
    for val in size:
        if not isinstance(val, int) or val == 0:
            raise ValueError('Invalid image size:' + repr(size))
    if bytes:
        if False in map(lambda x: x in 'RGBA', list(from_format)):
            raise ValueError('Converting from unsupported format: ' + from_format)
        if type(bytes) != int and len(bytes) < size[0]*size[1]*len(from_format):
            raise ValueError('Not enough bytes for converted format: expected %d, got %d' % \
                              (size[0]*size[1]*len(from_format), len(bytes)))
        return Image(_Imlib2.create(size, bytes, from_format, copy))
    else:
        return Image(_Imlib2.create(size))
