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

# displays imports
from bitmapcanvas import *



class Imlib2Canvas(BitmapCanvas):

    def __init__(self, size, dither = True, blend = False):
        super(Imlib2Canvas, self).__init__(size, preserve_alpha = blend)
        self._display = imlib2.Display(size, dither, blend)
        self._display.set_cursor_hide_timeout(1)

    def _blit(self, img, r):
        pos, size = r
        if not self._display.backing_store:
            # Sets the backing store for the Imlib2 display for default
            # expose handler.
            # FIXME: this requires app to call canvas._display.handle_events()
            # Need to offer an API within mevas for this.
            if self.alpha < 255:
                bs = self._backing_store_with_alpha
            else:
                bs = self._backing_store

            # We can only use the canvas backing store image if it's an
            # Imlib2 image.
            if isinstance(bs, mevas.imagelib.get_backend("imlib2").Image):
                self._display.set_backing_store(self._backing_store._image)

        if isinstance(img, mevas.imagelib.get_backend("imlib2").Image):
            self._display.render(img._image, pos, pos, size)
        else:
            if img.size != size:
                img = imagelib.crop(img, pos, size)

            data = img.get_raw_data("RGB")
            img = imlib2.new( size, data, "RGB" )
            self._display.render(img, pos)
