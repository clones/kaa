# -*- coding: iso-8859-1 -*-
# -----------------------------------------------------------------------------
# imlib2canvas.py - output display for imlib2 window
# -----------------------------------------------------------------------------
# $Id$
#
# -----------------------------------------------------------------------------
# Mevas - MeBox Canvas System
# Copyright (C) 2004-2005 Jason Tackaberry <tack@sault.org>
#
# First Edition: Jason Tackaberry <tack@sault.org>
# Maintainer:    Dirk Meyer <dmeyer@tzi.de>
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


# imlib2
from kaa import imlib2

# mevas imports
from kaa import mevas
from kaa.mevas.rect import optimize_for_rendering

# kaa imports
from kaa import display
from bitmapcanvas import *



class Imlib2Canvas(BitmapCanvas):

    def __init__(self, size, dither = True, blend = False):
        super(Imlib2Canvas, self).__init__(size, preserve_alpha = blend)
        self._dither, self._blend = dither, blend
        self._window = display.X11Window(size = size, title = "Mevas")
        self._window.set_cursor_hide_timeout(1)
        self._window.show()
        self._window.signals["expose_event"].connect(self._expose)
        self.__render = self._window.render_imlib2_image


    def _expose( self, regions ):
        """
        Callback for expose events from X11
        """
        if self.alpha < 255:
            bs = self._backing_store_with_alpha
        else:
            bs = self._backing_store
        for pos, size in optimize_for_rendering(regions):
            self.__render( bs._image, pos, pos, size )


    def _blit(self, img, r):
        pos, size = r
        if isinstance(img, mevas.imagelib.get_backend("imlib2").Image):
            self.__render(img._image, pos, pos, size, self._dither,
                          self._blend)
        else:
            if img.size != size:
                img = imagelib.crop(img, pos, size)

            data = img.get_raw_data("RGB")
            img = imlib2.new( size, data, "RGB" )
            self.__render(img._image, pos, dither = self._dither,
                          blend = self._blend)
