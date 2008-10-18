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

# python imports
import types
import math
import os

# imlib2 wrapper
import _Imlib2
from kaa import Signal
from kaa.strutils import utf8
from font import *


def get_max_rectangle_size((w, h), (max_w, max_h)):
    """
    Returns the aspect-preserved dimensions for the rectangle (w, h) that fit
    within the maximum rectangle specified by (max_w, max_h).
    """
    src_aspect = float(w) / h
    if float(max_w) / max_h > src_aspect:
        return int(max_h * src_aspect), max_h
    else:
        return max_w, int(max_w / src_aspect)


class Image(object):
    """
    Imlib2 Image class. The constructor can be called directly, or a
    new Image object may be created via the new() and open() module
    functions.  Instantiate the image from another Image instance, an
    instance of the backend's image class or type, or a file name from
    which to load the image.
    """

    def __init__(self, image_or_filename, use_cache=True):
        """
        Create a new Image object.
        """
        if type(image_or_filename) in types.StringTypes:
            self._image = _Imlib2.open(image_or_filename, use_cache)
        elif isinstance(image_or_filename, Image):
            self._image = image_or_filename.copy()._image
        elif type(image_or_filename) == _Imlib2.Image:
            self._image = image_or_filename
        else:
            raise ValueError, 'Unsupported image type %s' % type(image_or_filename)

        self.font = None
        self.signals = {
            'changed': Signal()
        }


    def __getattr__(self, attr):
        """
        Supports these attributes:
         - size: tuple containing the width and height of the image
         - width: width of the image
         - height: height of the image
         - format: format of the image if loaded from file (e.g. PNG, JPEG)
         - rowstride: number of bytes per row of pixels
         - has_alpha: True if the image has an alpha channel, False otherwise
         - filename: filename if loaded from file
        """
        if attr in ('width', 'height', 'format', 'mode', 'filename', 'rowstride'):
            return getattr(self._image, attr)
        elif attr == 'size':
            return (self._image.width, self._image.height)
        elif attr == 'has_alpha':
            if self._image.has_alpha: return True
            return False

        if attr not in self.__dict__:
            raise AttributeError, attr
        return self.__dict__[attr]


    # Functions for pickling.
    def __getstate__(self):
        return self.size, str(self.get_raw_data())

    def __setstate__(self, state):
        self._image = _Imlib2.create(state[0], state[1])


    def _changed(self):
        self.signals['changed'].emit()

    def get_raw_data(self, format = 'BGRA', write = False):
        """
        Returns raw image data for read only access. *format* is pixel
        format of the raw data to be returned. If it is not a
        supported format, ValueError is raised. Format can be any
        combination of RGB or RGBA. The function returns a buffer
        object representing the raw pixel data.  The buffer will be a
        writable buffer if 'write' was True or if the 'format' was
        non-native (i.e. something other than BGRA).  If 'format' was
        BGRA and 'write' was True, you'll need to call
        put_back_raw_data() when you're done writing to the buffer.
        """
        if False in map(lambda x: x in 'RGBA', list(format)):
            raise ValueError, 'Converting from unsupported format: ' + format
        return self._image.get_raw_data(format, write)


    def put_back_raw_data(self, data):
        """
        Puts back the writable buffer that was obtained with get_raw_data().
        """
        self._image.put_back_raw_data(data)
        self._changed()


    def scale(self, (w, h), src_pos = (0, 0), src_size = (-1, -1)):
        """
        Scale the image and return a new image. If either width or
        height is -1, that dimension is calculated from the other
        dimension while retaining the original aspect ratio.
        """
        src_w, src_h = src_size
        x, y = src_pos

        if 0 in src_size:
            raise ValueError, 'Invalid scale size specified %s' % repr(src_size)

        aspect = float(self.width) / float(self.height)
        if w == -1:
            w = round(h * aspect)
        elif h == -1:
            h = round(w / aspect)
        if src_w == -1:
            src_w = self.width
        if src_h == -1:
            src_h = self.height
        return Image(self._image.scale(int(x), int(y), int(src_w), int(src_h), int(w), int(h)))


    def crop(self, (x, y), (w, h)):
        """
        return a new Image which is croped at x,y with the given size.
        """
        return self.scale((w, h), (x, y), (w, h) )


    def rotate(self, angle):
        """
        Rotate the image by the angle in degrees and return a new
        image. Note: imlib2's rotate works all wonky.  Doesn't act how
        expected for angles different than 90, 180 and 270.
        """
        return Image(self._image.rotate(angle * math.pi / 180))


    def orientate(self, orientation):
        """
        Performs 90 degree rotations on the image. Possible values are
        0 (no rotation), 1 (rotate clockwise 90 degrees), 2 (rotate
        clockwise 180 degrees) and 3 (rotates clockwise 270 degrees).
        """
        self._image.orientate(orientation)
        self._changed()


    def flip_horizontal(self):
        """
        Flips the image on its horizontal axis.
        """
        self._image.flip(True, False, False)
        self._changed()


    def flip_vertical(self):
        """
        Flips the image on its vertical axis.
        """
        self._image.flip(False, True, False)
        self._changed()


    def flip_diagonal(self):
        """
        Flips the image on along its diagonal.
        """
        self._image.flip(False, False, True)
        self._changed()


    def blur(self, radius):
        """
        Blur the image
        """
        self._image.blur(radius)
        self._changed()


    def sharpen(self, radius):
        """
        Sharpen the image
        """
        self._image.sharpen(radius)
        self._changed()


    def scale_preserve_aspect(self, (w, h)):
        """
        Scales the image while retaining the original aspect ratio and
        return a new image. The given size is the maximum size of the
        new image.  The new image will be as large as possible, using
        w, h as the upper limits, while retaining the original aspect
        ratio.
        """
        if 0 in (w, h):
            raise ValueError, 'Invalid scale size specified %s' % repr((w,h))

        dst_w, dst_h = get_max_rectangle_size(self.size, (w, h))

        if self.size == (dst_w, dst_h):
            # No scale, just copy.
            return self.copy()

        return Image(self._image.scale(0, 0, self.width, self.height, dst_w, dst_h))


    def thumbnail(self, (w, h)):
        """
        Generates a thumbnail of the image, REPLACING the current image.
        This simulates the PIL thumbnail function.
        """
        if self.width < w and self.height < h:
            return

        self._image = self.scale_preserve_aspect( (w, h) )._image
        self._changed()


    def copy_rect(self, src_pos, size, dst_pos):
        """
        Copies a region within the image.

        :param src_pos: a tuple holding the x, y coordinates marking the top left
            of the region to be moved.
        :param size: a tuple holding the width and height of the region to move.
            If either dimension is -1, then that dimension extends to the far edge
            of the image.
        :param dst_pos: a tuple holding the x, y coordinates within the image
            where the region will be moved to.
        """
        self._image.copy_rect(src_pos, size, dst_pos)
        self._changed()


    def blend(self, src, src_pos = (0, 0), src_size = (-1, -1),
              dst_pos = (0, 0), dst_size = (-1, -1),
              alpha = 255, merge_alpha = True):
        """
        Blends one image onto another.

        :param src: the image being blended onto 'self'
        :param dst_pos: a tuple holding the x, y coordinates where the source
            image will be blended onto the destination image.
        :param src_pos: a tuple holding the x, y coordinates within the source
            image where blending will start.
        :param src_size: a tuple holding the width and height of the source
            image to be blended.  A value of -1 for either one
            indicates the full dimension of the source image.
        :param alpha: the "layer" alpha that is applied to all pixels of the
            image.  If an individual pixel has an alpha of 128 and
            this value is 128, the resulting pixel will have an
            alpha of 64 before it is blended to the destination
            image.  0 is fully transparent and 255 is fully opaque,
            and 256 is a special value that means alpha blending is
            disabled.
        :param merge_alpha: if True, the alpha channel is also blended.  If False,
            the destination image's alpha channel is untouched and
            the RGB values are compensated
        """

        if src_size[0] == -1:
            src_size = src.width, src_size[1]
        if src_size[1] == -1:
            src_size = src_size[0], src.height
        if dst_size[0] == -1:
            dst_size = src_size[0], dst_size[1]
        if dst_size[1] == -1:
            dst_size = dst_size[0], src_size[1]
        self._image.blend(src._image, src_pos, src_size, dst_pos, dst_size, int(alpha), merge_alpha)
        self._changed()


    def clear(self, (x, y) = (0, 0), (w, h) = (-1, -1)):
        """
        Clears the image at the specified rectangle, resetting all
        pixels in that rectangle to fully transparent. if either width
        or height of the rectangle to be cleared is -1 then the image
        is cleared to the far edge. Default values clear the whole image.
        """
        x = max(0, min(self.width, x))
        y = max(0, min(self.height, y))
        if w == -1:
            w = self.width - x
        if h == -1:
            h = self.height - y
        w = min(w, self.width-x)
        h = min(h, self.height-y)
        self._image.clear(x, y, w, h)
        self._changed()


    def draw_mask(self, maskimg, (x, y)):
        """
        Applies the luma channel of maskimg to the alpha channel of the
        the current image.

        Arguments:
          maskimg: the image from which to read the luma channel
             x, y: the top left coordinates within the current image where the
                   alpha channel will be modified.  The mask is drawn to the
                   full width/height of maskimg.
        """

        self._image.draw_mask(maskimg._image, int(x), int(y))
        self._changed()


    def copy(self):
        """
        Creates a copy of the current image.
        """
        return Image(self._image.clone())


    def set_font(self, font_or_font_name):
        """
        Sets the font context to font_or_font_name.  Subsequent calls
        to draw_text() will be rendered using this font.
        font_or_fontname is either a Font object, or a string
        containing the font's name and size.  This string is in the
        form 'Fontname/Size' such as 'Arial/16'

        The function returns a Font instance represent the specified
        font.  If 'font_or_fontname' is already a Font instance, it is
        simply returned back to the caller.
        """
        if type(font_or_font_name) in types.StringTypes:
            self.font = Font(font_or_font_name)
        else:
            self.font = font_or_font_name
        return self.font


    def get_font(self):
        """
        Gets the current Font context. Either the Font instance as
        created by set_font() or None if no font context is defined.
        """
        return self.font


    def draw_text(self, (x, y), text, color = None, font_or_fontname = None,
                  style = None, shadow = None, outline = None, glow = None,
                  glow2 = None):
        """
        Draws text on the image.

        :param x, y: the left/top coordinates within the current image
            where the text will be rendered.
        :param text: a string holding the text to be rendered.
        :param color: a 3- or 4-tuple holding the red, green, blue, and
            alpha values of the color in which to render the
            font.  If color is a 3-tuple, the implied alpha
            is 255.  If color is None, the color of the font
            context, as specified by set_font(), is used.
        :param font_or_fontname: either a Font object, or a string containing the
            font's name and size.  This string is in the
            form "Fontname/Size" such as "Arial/16".  If this
            parameter is none, the font context is used, as
            specified by set_font().
        :param style: The style to use. Id style is None, the style from
            the font object will be used.

        :return: a 4-tuple representing the width, height, horizontal advance,
            and vertical advance of the rendered text.
        """
        if not font_or_fontname:
            font = self.font
        elif type(font_or_fontname) in types.StringTypes:
            font = Font(font_or_fontname)
        else:
            font = font_or_fontname

        if not color:
            color = font.color
        elif len(color) == 3:
            color = tuple(color) + (255,)

        if style == TEXT_STYLE_PLAIN or (style == None and font.style == TEXT_STYLE_PLAIN):
            metrics = self._image.draw_text(font._font, int(x), int(y), utf8(text), color)
        else:
            if not style:
                style = font.style
            if not shadow:
                shadow = font.shadow
            elif len(shadow) == 3:
                shadow = tuple(shadow) + (255,)
            if not outline:
                outline = font.outline
            elif len(outline) == 3:
                outline = tuple(outline) + (255,)
            if not glow:
                glow = font.glow
            elif len(glow) == 3:
                glow = tuple(glow) + (255,)
            if not glow2:
                glow2 = font.glow2
            elif len(glow2) == 3:
                glow2 = tuple(glow2) + (255,)

            metrics = self._image.draw_text_with_style(font._font, int(x), int(y),
                                                       utf8(text), style, color,
                                                       shadow, outline, glow, glow2)
        self._changed()
        return metrics



    def draw_rectangle(self, (x, y), (w, h), color, fill = True):
        """
        Draws a rectangle on the image.

        :param x, y: the top left corner of the rectangle.
        :param w, h: the width and height of the rectangle.
        :param color: a 3- or 4-tuple holding the red, green, blue, and alpha
            values of the color in which to draw the rectangle.  If
            color is a 3-tuple, the implied alpha is 255.
        :param fill: whether the rectangle should be filled or not.  The default
            is true.
        """
        if len(color) == 3:
            color = tuple(color) + (255,)
        self._image.draw_rectangle(int(x), int(y), int(w), int(h), color, fill)
        self._changed()

    def draw_ellipse(self, (xc, yc), (a, b), color, fill = True):
        """
        Draws an ellipse on the image.

        :param xc, yc: the x, y coordinates of the center of the ellipse.
        :param a, b: the horizontal and veritcal amplitude of the ellipse.
        :param color: a 3- or 4-tuple holding the red, green, blue, and alpha
            values of the color in which to draw the ellipse.  If
            color is a 3-tuple, the implied alpha is 255.
        :param fill: whether the ellipse should be filled or not.  The default
            is true.
        """
        if len(color) == 3:
            color = tuple(color) + (255,)
        self._image.draw_ellipse(int(xc), int(yc), int(a), int(b), color, fill)
        self._changed()


    def get_pixel(self, (x, y)):
        """
        Get the color for the specified pixel as a 4-tuple
        representing the color of the pixel.  The tuple is in RGBA
        format, or (red, green, blue, alpha).
        """
        return self._image.get_pixel((x,y))


    def set_alpha(self, has_alpha):
        """
        Enable / disable the alpha layer. If has_alpha is True, the
        alpha layer will be enabled, if False disabled
        """
        if has_alpha:
            self._image.set_alpha(1)
        else:
            self._image.set_alpha(0)
        self._changed()


    def save(self, filename, format = None):
        """
        Saves the image to a file. The format for the written file
        (jpg, png, etc.) is gotten from the filename extension if not
        format is provided.
        """
        if not format:
            format = os.path.splitext(filename)[1][1:]
        return self._image.save(filename, format)


    def as_gdk_pixbuf(self):
        """
        Convert the image into a gdk.Pixbuf object. This function will
        either return a gdk.Pixbuf object or raises an ImportError if
        pygtk is unavailable.
        """
        import gtk
        data = self.get_raw_data('RGBA')
        return gtk.gdk.pixbuf_new_from_data(data, gtk.gdk.COLORSPACE_RGB, True, 8,
                                            self.width, self.height, self.width * 4)

