# -*- coding: iso-8859-1 -*-
# -----------------------------------------------------------------------------
# fbcanvas.py - output canvas for framebuffer
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

# kaa display imports
import kaa.display.fb

# mevas imports
from kaa import mevas

# displays import
from bitmapcanvas import *

class FramebufferCanvas(BitmapCanvas):

    def __init__(self, size, tv_format=''):
        fbset = tv_format.upper() + '_%sx%s' % size
        if hasattr(kaa.display.fb, fbset):
            fbset = getattr(kaa.display.fb, fbset)
        else:
            fbset = None
        self._fb = kaa.display.fb.Framebuffer(fbset)
        if self._fb.size() != size:
            del self._fb
            raise AttributeError('size does not match framebuffer')
        super(FramebufferCanvas, self).__init__(size, preserve_alpha = False)
        self._rect = []


    def _update_end(self, object = None):
        if not self._rect:
            return
        self._fb.set_image(self._backing_store._image)
        self._fb.update()
        self._rect = []


    def _blit(self, img, r):
        self._rect.append(r)

    def __del__(self):
        del self.fbset
        super(FramebufferCanvas, self).__del__()
