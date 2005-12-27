# -*- coding: iso-8859-1 -*-
# -----------------------------------------------------------------------------
# fb.py - Framebuffer Display
# -----------------------------------------------------------------------------
# $Id$
#
# -----------------------------------------------------------------------------
# kaa-display - X11/SDL Display module
# Copyright (C) 2005 Dirk Meyer, Jason Tackaberry
#
# First Edition: Dirk Meyer <dmeyer@tzi.de>
# Maintainer:    Dirk Meyer <dmeyer@tzi.de>
#
# Please see the file doc/CREDITS for a complete list of authors.
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

__all__ = [ 'PAL_768x576', 'PAL_800x600', 'NTSC_640x480', 'NTSC_768x576',
            'NTSC_800x600', 'Framebuffer', 'EvasFramebuffer' ]

import _FBmodule as fb

# modelines for tv out
PAL_768x576  = (768, 576, 768, 576, 0, 0, 0, 0, 38400, 20, 10, 30, 10, 10, 34, 19, 0)
PAL_800x600  = (800, 600, 800, 600, 0, 0, 0, 0, 38400, 48, 24, 70, 32, 2, 40, 19, 0)
NTSC_640x480 = (640, 480, 640, 480, 0, 0, 0, 0, 35000, 36, 6, 22, 22, 1, 46, 0, 0)
NTSC_768x576 = (768, 576, 768, 576, 0, 0, 0, 0, 35000, 36, 6, 39, 10, 4, 46, 0, 0)
NTSC_800x600 = (800, 600, 800, 600, 0, 0, 0, 0, 39721, 48, 24, 80, 32, 2, 40, 1, 0)

# modelines for monitor use
FB_800x600   = (800, 600, 800, 600, 0, 0, 0, 0, 20203, 160, 16, 21, 1, 80, 3, 0, 0)
FB_1024x768  = (1024, 768, 1024, 768, 0, 0, 0, 0, 13334, 104, 24, 29, 3, 136, 6, 0, 0)
FB_1280x1024 = (1280, 1024, 1280, 3264, 0, 0, 0, 0, 7414, 232, 64, 38, 1, 112, 3, 0, 0)
FB_1600x1200 = (1600, 1200, 1600, 1200, 0, 0, 0, 0, 6411, 256, 32, 52, 10, 160, 8, 0, 0)


class _Framebuffer(object):
    """
    Basic framebuffer class.
    The 'mode' argument can either be a size (width, height) matching one of the
    specified framebuffer resolutions, a list for fbset or None. If set to None,
    the current framebuffer size will be used.
    """
    def __init__(self, mode=None):
        if mode:
            if len(mode) == 2:
                mode = globals()['FB_%sx%s' % mode]
            fb.open(mode)
        else:
            fb.open()

    def info(self):
        """
        Return some basic informations about the frambuffer.
        """
        return fb.info()
    
    def size(self):
        """
        return the size of the framebuffer.
        """
        return fb.size()

    def __del__(self):
        fb.close()


class Framebuffer(_Framebuffer):
    """
    Frambuffer using an imlib2 image for drawing
    The 'mode' argument can either be a size (width, height) matching one of the
    specified framebuffer resolutions, a list for fbset or None. If set to None,
    the current framebuffer size will be used.
    """
    def __init__(self, mode=None):
        _Framebuffer.__init__(self, mode)
        import kaa.imlib2
        self.image = kaa.imlib2.new(fb.size())


    def set_image(self, image):
        """
        Set an imlib2 image to the frambuffer. The size of the image must match
        the current framebuffer resolution.
        """
        if (image.width, image.height) != fb.size():
            raise AttributeError('Invalid image size')
        self.image = image


    def blend(self, src, src_pos = (0, 0), dst_pos = (0, 0)):
        """
        Blend an imlib2 image to the framebuffer.
        """
        self.image.blend(src, src_pos=src_pos, dst_pos=dst_pos)


    def update(self):
        """
        Update the framebuffer.
        """
        fb.update(self.image._image)


class EvasFramebuffer(_Framebuffer):
    """
    Frambuffer using evas for drawing
    The 'mode' argument can either be a size (width, height) matching one of the
    specified framebuffer resolutions, a list for fbset or None. If set to None,
    the current framebuffer size will be used.
    """
    def __init__(self, mode=None):
        _Framebuffer.__init__(self, mode)
        import kaa.evas
        self._evas = kaa.evas.Evas()
        fb.new_evas_fb(self._evas._evas)

        
    def get_evas(self):
        """
        Return evas object.
        """
        return self._evas
