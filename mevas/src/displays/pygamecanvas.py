# -*- coding: iso-8859-1 -*-
# -----------------------------------------------------------------------------
# pygamecanvas.py - output canvas for pygame (SDL)
# -----------------------------------------------------------------------------
# $Id$
#
# -----------------------------------------------------------------------------
# kaa-mevas - MeBox Canvas System
# Copyright (C) 2004-2005 Jason Tackaberry <tack@sault.org>
#
# First Edition: Dirk Meyer <dmeyer@tzi.de>
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

# pygame (SDL) imports
import pygame
from pygame.locals import *

# mevas imports
from kaa import mevas
import kaa.mevas.rect as rect
import kaa.display.sdl

# displays import
from bitmapcanvas import *

class PygameCanvas(BitmapCanvas):

    def __init__(self, size):
        super(PygameCanvas, self).__init__(size, preserve_alpha = False)
        self._window = kaa.display.sdl.PygameDisplay(size)
        self._rect = []


    def _update_end(self, object = None):
        if not self._rect:
            return
        self._window.render_imlib2_image(self._backing_store._image._image, self._rect)
        self._rect = []


    def _blit(self, img, r):
        if isinstance(img, mevas.imagelib.get_backend("imlib2").Image):
            pass
        elif isinstance(img, mevas.imagelib.get_backend("pygame").Image):
            # FIXME: add code for native pygame images here.
            pass
        else:
            # FIXME: add code for not imlib2 images here
            pass
        self._rect.append(r)
