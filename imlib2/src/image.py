# -*- coding: iso-8859-1 -*-
# -----------------------------------------------------------------------------
# image.py - An Imlib2 image class
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

__all__ = [
    'open', 'open_without_cache', 'open_from_memory', 'new', 'get_cache_size',
    'set_cache_size', 'get_max_rectangle_size', 'Image', 'open_svg',
    'open_svg_from_memory'
]

# python imports
import types
import math
import os
import errno

# imlib2 wrapper
import _Imlib2
from kaa import Signal, Object
from kaa.utils import property
from kaa.strutils import utf8
from font import *


def _open_with_error_handle(open, *args):
    """
    Raises an IOError based on an Imlib2 error code.  Unfortunately Imlib2
    replaces perfectly good errno values with custom codes.  We effectively
    undo this conversion here.
    """
    try:
        return open(*args)
    except IOError, exc:
        if len(exc.args) != 1 or not exc.args[0].isdigit():
            raise

        map = [None, errno.ENOENT, errno.EISDIR, errno.EACCES, None, errno.ENAMETOOLONG,
               errno.ENOENT, errno.ENOTDIR, errno.EFAULT, errno.ELOOP, errno.ENOMEM, 
               errno.EMFILE, errno.EACCES, errno.EROFS]

        filename = args[0] if type(args[0]) == str else '<memory>'
        errcode = int(exc.args[0])
        if errcode == 4:
            raise IOError("No loader for file format: '%s'" % filename)
        elif errcode > 0 and errcode < len(map):
            raise IOError(map[errcode], "%s: '%s'" % (os.strerror(map[errcode]), filename))
        else:
            raise IOError("Unknown error occurred (unsupported format?): '%s'" % filename)


def open(filename, size=None):
    """
    Decode an image from disk.

    :param filename: path to the file to open
    :type filename: str
    :param size: initial width and height of the image; if either dimension is
                 -1, it will be computed based on aspect ratio; if *size* is
                 None, use the default image size.
    :type size: 2-tuple of ints
    :returns: :class:`~imlib2.Image` object

    kaa.imlib2 (unlike Imlib2 natively) supports rasterization of SVG images.
    however detection is based on file extension.  If you need to rasterize
    an SVG file that doesn't have a ``.svg`` extension, you will need to
    use :func:`~imlib2.open_from_memory`.

    For non-SVG images, this function will cache the raw image data of the
    loaded file, so that subsequent invocations with the given filename will
    load from cache.

    >>> from kaa import imlib2
    >>> imlib2.open('file.jpg')
    <kaa.imlib2.Image object size=1920x1080 0x9347eac>
    # SVGs can be loaded the same way.
    >>> imlib2.open('image.svg', size=(640, -1))
    <kaa.imlib2.Image object size=640x371 at 0xb69df84c>
    """
    if filename.lower().endswith('.svg'):
        return open_from_memory(file(filename).read(), size)
    else:
        return Image(filename, True, size)


def open_without_cache(filename, size=None):
    """
    Decode an image from disk without looking in the cache (or storing
    the result in the cache).

    :param filename: path to the file to open
    :type filename: str
    :param size: initial width and height of the image; if either dimension is
                 -1, it will be computed based on aspect ratio; if *size* is
                 None, use the default image size.
    :type size: 2-tuple of ints
    :returns: :class:`~imlib2.Image` object
    """
    if filename.lower().endswith('.svg'):
        return open_from_memory(file(filename).read(), size)
    else:
        return Image(filename, True, size)


def open_from_memory(buf, size=None):
    """
    Decode an image stored in memory.

    :param buf: encoded image data
    :type buf: str or buffer
    :param size: initial width and height of the image; if either dimension is
                 -1, it will be computed based on aspect ratio; if *size* is
                 None, use the default image size.
    :type size: 2-tuple of ints
    :returns: :class:`~imlib2.Image` object

    .. note:: Due to limitations in Imlib2, this function uses POSIX shared
       memory if it's available (such as on Linux).  If it's not available, a
       temporary file will be created in /tmp.

    >>> from kaa import imlib2
    # This example is a bit contrived because you could easily use open(), but
    # shows that if you have an existing buffer with encoded image data, you
    # can use this function to decode it into an Image object.
    >>> data = file('file.jpg').read()
    >>> imlib2.open_from_memory(data)
    <kaa.imlib2.Image object size=1920x1080 0x9347eac>
    """
    if type(buf) == str:
        buf = buffer(buf)
    if buf[:4].lower() == '<svg' or '\n<svg' in buf[:512].lower():
        if not size:
            size = 0,0
        w, h, buf = _Imlib2.render_svg_to_buffer(size[0], size[1], buf)
        return new((w,h), buf, from_format='RGBA', copy=False)
    else:
        # Other image
        img = _open_with_error_handle(_Imlib2.open_from_memory, buf)
        return Image(img, size=size)


def open_svg_from_memory(data, size=None):
    """
    Deprecated: use :func:`~imlib2.open_from_memory`.
    """
    return open_from_memory(data, size)


def open_svg(filename, size=None):
    """
    Deprecated: use :func:`~imlib2.open`.
    """
    return open_from_memory(file(filename).read(), size)


def new(size, bytes=None, from_format='BGRA', copy=True):
    """
    Create a new Image object (optionally) from existing raw data.

    :param size: width and height of the image to create
    :type size: 2-tuple of ints
    :param bytes: raw image data from which to initialize the image, which must be
                  in the RGB colorspace; if an int, specifies a pointer to a
                  location in memory holding the raw image (default: None)
    :type bytes: str, buffer, int, None
    :param from_format: specifies the pixel format of the supplied raw data;
                        can be any permutation of ``RGB`` or ``RGBA``.
                        (default: ``BGRA``, which is Imlib2's native pixel
                        format).
    :type from_format: str
    :param copy: if True, the raw data *bytes* will be copied to the Imlib2
                 object. If False, *bytes* must be either a writable buffer
                 or an integer pointing to a location in memory; in this case,
                 if *from_format* is ``BGRA`` then Imlib2 will directly use
                 the supplied buffer; if it's not ``BGRA`` then a colorspace
                 conversion is necessary, but an in-place conversion will be
                 done if possible.
    :type copy: bool
    :returns: :class:`~imlib2.Image` object

    *bytes* can be an integer, acting as a pointer to memory, which is useful
    with interoperating with other libraries, however this should be used with
    extreme care as incorrect values can segfault the interpeter.

    .. warning:: Formats (e.g. ``BGRA``) indicate the byte order when the image
       is viewed as a memory buffer on little-endian machines.  Each pixel is a
       32-bit quantity where blue is stored in the least significant byte and
       alpha is the most significant byte.  On big-endian architectures, the
       format ``BGRA`` is actually stored in the order ``ARGB``.

    >>> from kaa import imlib2
    # Create a new, blank 1920x1080 image.
    >>> imlib2.new((1920, 1080))
    <kaa.imlib2.Image object size=1920x1080 at 0x9c0dbec>
    # Create a new 1024x768 image initialized from existing data (all pixels
    # 50% opaque red)
    >>> imlib2.new((1024, 768), bytes='\\x00\\x00\\xff\\x7f' * 1024 * 768)
    <kaa.imlib2.Image object size=1024x768 at 0x9c79d4c>
    # Create a new 1024x768 image initialized from 24-bit data whose pixel
    # order is RGB.  (Alpha channel is initialized to 255)
    >>> imlib2.new((1024, 768), bytes='\\xff\\x00\\x00' * 1024 * 768, from_format='RGB')
    <kaa.imlib2.Image object size=1024x768 at 0x9c79dec>

    The following code shows how you can use the array type to share a writable
    buffer:

    >>> import array
    # Initialize an array with 50% opaque purple.
    >>> data = array.array('c', '\\xff\\x00\\xff\\x7f' * 1024 * 768)
    # Create the image with copy=False so we share the buffer.
    >>> img = imlib2.new((1024, 768), data, copy=False)
    # Note the value of the first pixel.
    >>> data[:4]
    array('c', '\\xff\\x00\\xff\\x7f')
    # Clear the image and look at the same pixel, note how it's changed in the
    # buffer.
    >>> img.clear()
    >>> data[:4]
    array('c', '\\x00\\x00\\x00\\x00')

    Although you can use writable buffers directly as in the above example,
    you can also pass a integer which represents a pointer to the buffer.

    >>> data = array.array('c', '\\xff\\x00\\xff\\x7f' * 1024 * 768)
    >>> ptr, len = data.buffer_info()
    >>> ptr
    3022487560L
    >>> img = imlib2.new((1024, 768), ptr, copy=False)
    >>> img.clear()
    >>> data[:4]
    array('c', '\\x00\\x00\\x00\\x00')

    You would never actually do this for arrays, but if you have a pointer
    to a buffer returned by some other library (gotten through ctypes, perhaps),
    you can use the pointer as a buffer.  In this case, you maintain ownership
    over the buffer, and it is your responsibility to free it.
    """
    for val in size:
        if not isinstance(val, int) or val == 0:
            raise ValueError('Invalid image size:' + repr(size))
    if bytes:
        if False in map(lambda x: x in 'RGBA', list(from_format)):
            raise ValueError('Converting from unsupported format: ' + from_format)
        if not isinstance(bytes, (int, long)) and len(bytes) < size[0]*size[1]*len(from_format):
            raise ValueError('Not enough bytes for converted format: expected %d, got %d' % \
                              (size[0]*size[1]*len(from_format), len(bytes)))
        return Image(_Imlib2.create(size, bytes, from_format, copy))
    else:
        return Image(_Imlib2.create(size))


def get_cache_size():
    """
    Return the size of Imlib2's internal image cache.

    :returns: size in bytes of the cache
    """
    return _Imlib2.get_cache_size()

def set_cache_size(size):
    """
    Sets the size of Imlib2's internal image cache.

    :param size: size in bytes; a value of 0 will flush the cache and prevent
                 future caching.
    :type size: int
    
    When the cache size is set, Imlib2 will flush old images from the cache
    until the current cache usage is less than or equal to the cache size.

    .. note:: The cache size is initialized to 4MB.
    """
    _Imlib2.set_cache_size(size)


def get_max_rectangle_size((w, h), (max_w, max_h)):
    """
    Compute the largest rectangle that can fit within one given rectangle, while
    retaining the aspect ratio of the other given rectangle.

    :param w, h: the dimensions of the rectangle whose aspect ratio to preserve
    :type w, h: int
    :param max_w, max_h: the maximum dimensions of the computed rectangle
    :type max_w, max_h: int
    :returns: (width, height) of the bound, aspect-preserved rectangle
    """
    src_aspect = float(w) / h
    if float(max_w) / max_h > src_aspect:
        return int(max_h * src_aspect), max_h
    else:
        return max_w, int(max_w / src_aspect)



class Image(Object):
    """
    Image class representing an Imlib2 Image object.

    :param image_or_filename: another :class:`~imlib2.Image` object
                              to clone, or a filename of the encoded image
                              to load on disk.
    :type image_or_filename: :class:`~imlib2.Image` or str
    :param use_cache: if True, will use Imlib2's internal cache for image data
    :type use_cache: bool

    It is possible to create Image objects directly, but the
    :func:`imlib2.open` or :func:`imlib2.new` module functions are
    more likely to be useful.
    """
    __kaasignals__ = {
        'changed':
            '''
            Emitted when the image has been altered in some way.

            .. describe:: def callback(...)
            '''
    }

    def __init__(self, image_or_filename, use_cache=True, size=None):
        super(Image, self).__init__()
        if type(image_or_filename) in types.StringTypes:
            self._image = _open_with_error_handle(_Imlib2.open, image_or_filename, use_cache)
        elif isinstance(image_or_filename, Image):
            self._image = image_or_filename.copy()._image
        elif type(image_or_filename) == _Imlib2.Image:
            self._image = image_or_filename
        else:
            raise ValueError('Unsupported image type ' + type(image_or_filename).__name__)

        if size and size != self.size:
            self._image = self.scale(size)._image

        self._font = None


    def __repr__(self):
        return '<kaa.imlib2.%s object size=%dx%d at 0x%x>' % \
               (self.__class__.__name__, self.width, self.height, id(self))


    # Functions for pickling.
    def __getstate__(self):
        return self.size, str(self.get_raw_data()), self._font, self.has_alpha


    def __setstate__(self, state):
        # Invoke kaa.Object initializer to create self.signals.
        super(Image, self).__init__()
        size, data, font, has_alpha = state
        self._image = _Imlib2.create(size, data)
        self._font = font
        self.set_has_alpha(has_alpha)


    @property
    def width(self):
        """
        The width of the image in pixels.
        """
        return self._image.width


    @property
    def height(self):
        """
        The height of the image in pixels.
        """
        return self._image.height


    @property
    def size(self):
        """
        A 2-tuple of the width and height of the image in pixels.
        """
        return self._image.width, self._image.height


    @property
    def format(self):
        """
        The encoded format (e.g. 'png', 'jpeg') of the image if loaded from a
        file, None otherwise.
        """
        return self._image.format


    @property
    def mode(self):
        """
        The pixel format of the decoded image in memory (always ``BGRA``).
        """
        return self._image.mode


    @property
    def filename(self):
        """
        The filename of the image if lodaed from a file, None otherwise.
        """
        return self._image.filename


    @property
    def rowstride(self):
        """
        The number of bytes each row of pixels occupies in memory.

        This is typically width * 4.
        """
        return self._image.rowstride


    @property
    def has_alpha(self):
        """
        True if the image has an alpha channel, False otherwise.

        This can be changed via the :meth:`~imlib2.Image.set_has_alpha` method
        rather than setting this property, because
        :meth:`~imlib2.Image.set_has_alpha` has a side-effect of emitting the
        :attr:`~imlib2.Image.signals.changed` signal.

        """
        return bool(self._image.has_alpha)


    @property
    def font(self):
        """
        :class:`~imlib2.Font` object specifying font context used by
        :meth:`~imlib2.Image.draw_text`, or None if no font was set.

        >>> from kaa import imlib2
        >>> imlib2.auto_set_font_path()
        >>> img = imlib2.new((1920, 1080))
        >>> img.font = imlib2.Font('VeraBd/60', '#ff55ff')
        >>> img.font.set_style(imlib2.TEXT_STYLE_SOFT_SHADOW, shadow='#888888')
        >>> img.draw_text((100, 100), 'Hello World!')
        (557, 92, 557, 93)
        """
        return self._font

    @font.setter
    def font(self, font):
        if not isinstance(font, Font):
            raise ValueError('Must be a kaa.imlib2.Font object')
        self._font = font


    def _changed(self):
        self.signals['changed'].emit()


    def get_raw_data(self, format='BGRA', write=False):
        """
        Return the underlying raw data of the image.

        :param format: the pixel format of the returned buffer; must be a
                       permutation of RGB or RGBA (default: BGRA, Imlib2's
                       native pixel layout).
        :type format: str
        :param write: if True, the returned buffer will be writable.
        :type write: bool
        :returns: a read-only buffer (if *write* is False and *format* is
                  ``BGRA``) or a read-write buffer (if *write* is True or
                  *format* is not 'BGRA')

        When *format* is not ``BGRA`` (i.e. not Imlib2's native buffer), pixel
        format conversion will be performed and the converted raw data copied
        to a newly allocated buffer.  The returned buffer will therefore always
        be read-write.  Writing to this buffer will have no effect on the image.

        When *format* is ``BGRA``, the returned buffer will map directly onto
        Imlib2's underlying pixel buffer.  In this case, the returned buffer will
        only be read-write if *write* is True, which will allow you to directly
        manipulate the underlying buffer.  You must call
        :meth:`~imlib2.Image.put_back_raw_data` when you're done writing to the
        buffer.

        >>> from kaa import imlib2
        >>> img = imlib2.open('file.jpg')
        >>> buf = img.get_raw_data(write=True)
        # Set first pixel to white.
        >>> buf[:4] = '\xff' * 4
        >>> img.put_back_raw_data(buf)

        .. warning:: see :func:`imlib2.new` for more information on the pixel
           layout.  When modifying the buffer directly, you must be aware of
           the endianness of the machine.
        """
        if False in map(lambda x: x in 'RGBA', list(format)):
            raise ValueError('Converting from unsupported format: ' + format)
        return self._image.get_raw_data(format, write)


    def put_back_raw_data(self, data):
        """
        Put back the writable buffer that was obtained with
        :meth:`~imlib2.Image.get_raw_data`.

        :param data: the read-write buffer that was gotten from
                     :meth:`~imlib2.Image.get_raw_data`
        :type data: buffer

        Changes made directly to the buffer will not be reflected in the image
        until this method is called.  If you modify the buffer again, you must
        call this method again (but you needn't call
        :meth:`~imlib2.Image.get_raw_data` again).

        Calling this method will emit the :attr:`~imlib2.Image.signals.changed` signal.
        """
        self._image.put_back_raw_data(data)
        self._changed()


    def scale(self, size, src_pos=(0, 0), src_size=(-1, -1)):
        """
        Scale the image and return a new image.

        :param size: the width and height of scaled image; if either
                     width or height is -1, that dimension is calculated
                     from the other dimension while preserving the aspect
                     ratio.
        :type size: 2-tuple of ints
        :param src_pos: offset within the source image which will correspond
                        to position (0,0) in the scaled image.
        :type src_pos: 2-tuple of ints
        :param src_size: the amount of width and height of the source image to
                         include (scaled) in the new image; if either dimension
                         is -1, it will extend to the right or bottom border.
        :type src_size: 2-tuple of ints
        :returns: a new :class:`imlib2.Image` object
        """
        w, h = size
        src_w, src_h = src_size
        x, y = src_pos

        if 0 in src_size:
            raise ValueError('Invalid scale size specified ' + repr(src_size))

        aspect = float(self.width) / float(self.height)
        if w == -1:
            w = round(h * aspect)
        elif h == -1:
            h = round(w / aspect)

        src_w = src_w if src_w > 0 else self.width + src_w - x
        src_h = src_h if src_h > 0 else self.height + src_h - y
        return Image(self._image.scale(int(x), int(y), int(src_w), int(src_h), int(w), int(h)))


    def crop(self, (x, y), (w, h)):
        """
        Crop the image and return a new image.

        :param x, y: left/top offset of cropped image
        :type x, y: int
        :param w, h: width and height of the cropped image (offset at x);
                     values less than or equal to zero are relative to the
                     far edge of the image.
        :type w, h: int
        :returns: a new :class:`~imlib2.Image` object

        >>> from kaa import imlib2
        >>> img = imlib2.open('file.jpg')
        >>> img
        <kaa.imlib2.Image object size=1920x1080 at 0xb73cef6c>
        >>> img.crop((100, 100), (-100, -100))
        <kaa.imlib2.Image object size=1720x880 at 0x8a73f4c>
        """
        w = w if w > 0 else self.width + w - x
        h = h if h > 0 else self.height + h - y
        return Image(self._image.scale(int(x), int(y), int(w), int(h), int(w), int(h)))


    def rotate(self, angle):
        """
        Rotate the image and return a new image.

        :param angle: the angle in degrees to rotate
        :type angle: float
        :returns: a new :class:`~imlib2.Image` object

        The new image will be sized to fit the full contents of the rotated
        image, and likely quite a bit larger than it needs to be.

        >>> from kaa import imlib2
        >>> img = imlib2.open('file.png')
        >>> img.size
        (1920, 1080)
        >>> img.rotate(20).size
        (2208, 2208)
        """
        return Image(self._image.rotate(angle * math.pi / 180))


    def orientate(self, orientation):
        """
        Perform in-place 90 degree rotations on the image.

        :param orientation: 0 = no rotation, 1 = rotate clockwise 90 degrees,
                            2 = rotate clockwise 180 degrees, 3 = rotate
                            clockwise 270 degrees.
        :type orientation: int
        :returns: self

        Calling this method will emit the :attr:`~imlib2.Image.signals.changed` signal.
        """
        self._image.orientate(orientation)
        self._changed()
        return self


    def flip_horizontal(self):
        """
        Flip the image horizontally (along its vertical axis).

        :returns: self

        Calling this method will emit the :attr:`~imlib2.Image.signals.changed` signal.
        """
        self._image.flip(True, False, False)
        self._changed()
        return self


    def flip_vertical(self):
        """
        Flip the image vertically (along its horizontal axis).

        :returns: self

        Calling this method will emit the :attr:`~imlib2.Image.signals.changed` signal.
        """
        self._image.flip(False, True, False)
        self._changed()
        return self


    def flip_diagonal(self):
        """
        Flip the image on along its diagonal, so that the top-right corner is
        mapped to the bottom left.

        :returns: self

        In practice:

        >>> img.flip_diagonal()

        is equivalent to (but a bit faster than):
        
        >>> img.orientate(1).flip_horizontal()

        Calling this method will emit the :attr:`~imlib2.Image.signals.changed` signal.
        """
        self._image.flip(False, False, True)
        self._changed()
        return self


    def blur(self, radius):
        """
        Blur the image in-place.

        :param radius: the size of the blur matrix radius (higher values
                       produce more blur)
        :type radius: int
        :returns: self

        Calling this method will emit the :attr:`~imlib2.Image.signals.changed` signal.
        """
        self._image.blur(radius)
        self._changed()
        return self


    def sharpen(self, radius):
        """
        Sharpen the image in-place.

        :param radius: the size of the sharpen radius (higher values produce
                        greater sharpening)
        :type radius: int
        :returns: self

        Calling this method will emit the :attr:`~imlib2.Image.signals.changed` signal.
        """
        self._image.sharpen(radius)
        self._changed()
        return self


    def scale_preserve_aspect(self, (w, h)):
        """
        Scale the image while preserving the original aspect ratio and return a
        new image.

        :param w: the maximum width of the new image
        :type w: int
        :param w: the maximum height of the new image
        :type w: int
        :returns: a new :class:`~imlib2.Image` object

        The new image will be as large as possible, using *w* and *h* as
        the upper limits, while retaining the original aspect ratio.
        """
        if 0 in (w, h):
            raise ValueError('Invalid scale size specified ' + repr((w,h)))

        dst_w, dst_h = get_max_rectangle_size(self.size, (w, h))

        if self.size == (dst_w, dst_h):
            # No scale, just copy.
            return self.copy()

        return Image(self._image.scale(0, 0, self.width, self.height, dst_w, dst_h))


    def thumbnail(self, (w, h)):
        """
        Scale the image in-place, preserving the original aspect ratio.

        :param w: the maximum width of the new image
        :type w: int
        :param w: the maximum height of the new image
        :type w: int
        :returns: self

        This implements behaviour of the PIL function of the same name.

        Calling this method will emit the :attr:`~imlib2.Image.signals.changed` signal.
        """
        if self.width < w and self.height < h:
            # Already within the size limit
            return self

        self._image = self.scale_preserve_aspect( (w, h) )._image
        self._changed()
        return self


    def copy_rect(self, src_pos, size, dst_pos):
        """
        Copy a region within the image.

        :param src_pos: the x, y coordinates marking the top left of the region
                        to be moved.
        :type src_pos: 2-tuple of ints
        :param size: the width and height of the region to move.  If either
                     dimension is -1, then that dimension extends to the far
                     edge of the image.
        :type size: 2-tuple of ints
        :param dst_pos: the x, y coordinates within the image where the region
                        will be moved to.
        :type dst_pos: 2-tuple of ints
        :returns: self

        Calling this method will emit the :attr:`~imlib2.Image.signals.changed` signal.
        """
        w, h = size
        w = w if w > 0 else self.width + w - x
        h = h if h > 0 else self.height + h - y
        self._image.copy_rect(src_pos, (w, h), dst_pos)
        self._changed()
        return self


    def blend(self, src, src_pos=(0, 0), src_size=(-1, -1),
              dst_pos=(0, 0), dst_size=(-1, -1),
              alpha=255, merge_alpha=True):
        """
        Blend the supplied image onto the current image.

        :param src: the image being blended onto 'self'
        :type src: :class:`~imlib2.Image` object
        :param dst_pos: the x, y coordinates where the source image will be
                        blended onto the destination image
        :type dst_pos: 2-tuple of ints
        :param src_pos: the x, y coordinates within the source image where
                        blending will start.
        :type src_pos: 2-tuple of ints
        :param src_size: the width and height of the source image to be
                         blended.  A value of -1 for either one indicates the
                         full dimension of the source image.
        :type src_size: 2-tuple of ints
        :param alpha: the "layer" alpha that is applied to all pixels of the
                      image.  If an individual pixel has an alpha of 128 and
                      this value is 128, the resulting pixel will have an alpha
                      of 64 before it is blended to the destination image.  0
                      is fully transparent and 255 is fully opaque, and 256 is
                      a special value that means alpha blending is disabled.
        :type alpha: int
        :param merge_alpha: if True, the alpha channel is also blended.  If False,
                            the destination image's alpha channel is untouched
                            and the RGB values are compensated.
        :type merge_alpha: bool
        :returns: self

        This example overlays an image called ``a.jpg``, rotated 20 degrees
        and 60% opaque, onto an image called ``b.jpg`` at 50, 50.

        >>> from kaa import imlib2
        >>> img = imlib2.open('b.jpg')
        >>> img.blend(imlib2.open('a.jpg').rotate(20), dst_pos=(50, 50), alpha=60)

        Calling this method will emit the :attr:`~imlib2.Image.signals.changed` signal.
        """
        if src_size[0] == -1:
            src_size = src.width, src_size[1]
        if src_size[1] == -1:
            src_size = src_size[0], src.height
        if dst_size[0] == -1:
            dst_size = src_size[0], dst_size[1]
        if dst_size[1] == -1:
            dst_size = dst_size[0], src_size[1]

        self._image.blend(src._image, src_pos, src_size, (x, y), dst_size, int(alpha), merge_alpha)
        self._changed()
        return self


    def clear(self, pos=(0, 0), size=(0, 0)):
        """
        Clear the specified rectangle, resetting all pixels in that rectangle
        to fully transparent (``#0000``).

        :param pos: left/top corner of the rectangle
        :type pos: 2-tuple of ints
        :param size: width and height of the rectangle; if either value is less
                     than or equal to zero then they are relatve to the far edge
                     of the image
        :type size: 2-tuple of ints
        :returns: self
        
        If this method is called without arguments, the whole image will be cleared.

        Calling this method will emit the :attr:`~imlib2.Image.signals.changed` signal.
        """
        x, y = pos
        w, h = size
        w = w if w > 0 else self.width + w - x
        h = h if h > 0 else self.height + h - y
        self._image.clear(x, y, w, h)
        self._changed()
        return self


    def draw_mask(self, maskimg, pos=(0,0)):
        """
        Apply the luma channel of another image to the alpha channel of the
        current image.

        :param maskimg: the image from which to read the luma channel
        :type maskimg: :class:`~imlib2.Image` object
        :param pos: the left/top coordinates within the current image where the
                    alpha channel will be modified.  The mask is drawn to the
                    full width/height of maskimg.
        :returns: self

        This example creates a mask for an image with three vertical strips of
        different shades of white.   Once the mask is drawn to the image, the
        image will have three strips of different alpha values: 100% (255),
        73% (187), and 53% (136).

        >>> from kaa import imlib2
        >>> img = imlib2.open('file.jpg')
        >>> mask = imlib2.new(img.size)
        >>> mask.draw_rectangle((0, 0), (img.width/3, img.height), color='#ffffff')
        >>> mask.draw_rectangle((img.width/3, 0), (img.width/3, img.height), color='#bbbbbb')
        >>> mask.draw_rectangle((img.width/3*2, 0), (img.width/3, img.height), color='#888888')
        >>> img.draw_mask(mask)

        Calling this method will emit the :attr:`~imlib2.Image.signals.changed` signal.
        """
        x, y = pos
        self._image.draw_mask(maskimg._image, int(x), int(y))
        self._changed()
        return self


    def copy(self):
        """
        Create a copy of the current image.

        :returns: a new :class:`~imlib2.Image` object, copied from the
                  current image.

        .. note::
           
           Any callbacks connected to the :attr:`~imlib2.Image.signals.changed` signal
           will not be preserved in the copy.
        """
        return Image(self._image.clone())


    def set_font(self, font_or_font_name):
        """
        Deprecated: use the :attr:`~imlib2.Image.font` property instead.
        """
        if type(font_or_font_name) in types.StringTypes:
            self._font = Font(font_or_font_name)
        else:
            self._font = font_or_font_name
        return self._font


    def get_font(self):
        """
        Deprecated: use the :attr:`~imlib2.Image.font` property instead.
        """
        return self.font


    def draw_text(self, (x, y), text, color=None, font_or_fontname=None,
                  style=None, shadow=None, outline=None, glow=None,
                  glow2=None):
        """
        Draw text on the image, optionally stylized.

        :param x, y: the left/top coordinates within the current image
                     where the text will be rendered
        :type x, y: int
        :param text: the text to be rendered
        :type text: str or unicode
        :param color: any value supported by :func:`imlib2.normalize_color`;
                      if None, the color of the font context, as set by
                      :attr:`~imlib2.Image.font` property, is used.
        :type color: 3- or 4-tuple of ints
        :param font_or_fontname: Font object or 'font/size' (e.g. 'arial/16')
        :type font_or_font_name: :class:`~imlib2.Font` object or str
        :param style: the style to use to draw the supplied text. If style is
                      None, the style from the font object will be used.
        :type style: a :ref:`TEXT_STYLE <textstyles>` constant
        :returns: a 4-tuple representing the width, height, horizontal advance,
                  and vertical advance of the rendered text.

        >>> from kaa import imlib2
        >>> imlib2.auto_set_font_path()
        >>> img = imlib2.new((1920, 1080))
        # Assumes VeraBd.ttf is in the font path.
        >>> img.draw_text((100, 100), 'Hello World!', '#ff55ff', 'VeraBd/60',
        ...               style=imlib2.TEXT_STYLE_SOFT_SHADOW, shadow='#888888')
        (557, 92, 557, 93)

        Calling this method will emit the :attr:`~imlib2.Image.signals.changed` signal.
        """
        if not font_or_fontname:
            font = self.font
        elif type(font_or_fontname) in types.StringTypes:
            font = Font(font_or_fontname)
        else:
            font = font_or_fontname

        color = normalize_color(color or font.color)

        if style == TEXT_STYLE_PLAIN or (style == None and font.style == TEXT_STYLE_PLAIN):
            metrics = self._image.draw_text(font._font, int(x), int(y), utf8(text), color)
        else:
            style = style or font.style
            shadow = normalize_color(shadow or font.shadow)
            outline = normalize_color(outline or font.outline)
            glow = normalize_color(glow or font.glow)
            glow2 = normalize_color(glow2 or font.glow2)
            metrics = self._image.draw_text_with_style(font._font, int(x), int(y),
                                                       utf8(text), style, color,
                                                       shadow, outline, glow, glow2)
        self._changed()
        return metrics


    def draw_rectangle(self, (x, y), (w, h), color, fill=True):
        """
        Draw a rectangle (filled or outline) on the image.

        :param x, y: the top left corner of the rectangle
        :type x, y: int
        :param w, h: the width and height of the rectangle; values less than or
                     equal to zero are relative to the far edge
        :type w, h: int
        :param color: any value supported by :func:`imlib2.normalize_color`
        :param fill: True if the rectangle should be filled, False if outlined
        :type bool: bool
        :returns: self

        Calling this method will emit the :attr:`~imlib2.Image.signals.changed` signal.
        """
        w = w if w > 0 else self.width + w - x
        h = h if h > 0 else self.height + h - y
        self._image.draw_rectangle(int(x), int(y), int(w), int(h), normalize_color(color), fill)
        self._changed()
        return self


    def draw_ellipse(self, (xc, yc), (a, b), color, fill=True):
        """
        Draw an ellipse (filled or outline) on the image.

        :param xc, yc: the x, y coordinates of the center of the ellipse
        :type xc, xy: int
        :param a, b: the horizontal and veritcal amplitude of the ellipse
        :type a, b: int
        :param color: any value supported by :func:`imlib2.normalize_color`
        :param fill: True if the ellipse should be filled, False if outlined
        :type bool: bool
        :returns: self

        Calling this method will emit the :attr:`~imlib2.Image.signals.changed` signal.
        """
        self._image.draw_ellipse(int(xc), int(yc), int(a), int(b), normalize_color(color), fill)
        self._changed()
        return self


    def get_pixel(self, (x, y)):
        """
        Fetch the RGBA value of a specifix pixel.

        :param x, y: the coordinate of the pixel
        :type x, y: int
        :returns: 4-tuple of (red, green, blue, alpha) where each value is
                  between 0 and 255.
        """
        return self._image.get_pixel((x,y))


    def set_alpha(self, has_alpha):
        """
        Deprecated: use :meth:`~imlib2.Image.set_has_alpha` instead.
        """
        return self.set_has_alpha(has_alpha)


    def set_has_alpha(self, has_alpha):
        """
        Enable or disable the alpha channel.

        :param has_alpha: True if the alpha channel should be considered,
                          False if the image is the alpha channel should be
                          ignored (and the image is fully opaque)
        :type has_alpha: False

        Calling this method will emit the :attr:`~imlib2.Image.signals.changed` signal.
        """
        if has_alpha:
            self._image.set_alpha(1)
        else:
            self._image.set_alpha(0)
        self._changed()


    def save(self, filename, format=None):
        """
        Save the image to a file.

        :param filename: the output filename 
        :type filename: str
        :param format: the encoding format (jpeg, png, etc.); if None, will
                       be derived from the filename extension.
        :returns: self
        """
        if not format:
            format = os.path.splitext(filename)[1][1:]
        self._image.save(filename, format)
        return self


    def as_gdk_pixbuf(self):
        """
        Convert the image into a gdk.Pixbuf object.
        
        :raises: ImportError if pygtk is not available.
        :returns: a `gdk.Pixbuf <http://library.gnome.org/devel/pygtk/stable/class-gdkpixbuf.html>`_ 
                  object containing a copy of the image data

        >>> from kaa import imlib2
        >>> img = imlib2.open('file.png')
        >>> img.as_gdk_pixbuf()
        <gtk.gdk.Pixbuf object at 0x909334c (GdkPixbuf at 0x9452318)>
        """
        import gtk
        data = self.get_raw_data('RGBA')
        return gtk.gdk.pixbuf_new_from_data(data, gtk.gdk.COLORSPACE_RGB, True, 8,
                                            self.width, self.height, self.width * 4)
