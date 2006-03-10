# -*- coding: iso-8859-1 -*-
# -----------------------------------------------------------------------------
# display - Interface to the display code
# -----------------------------------------------------------------------------
# $Id$
#
# -----------------------------------------------------------------------------
# kaa-display - Generic Display Module
# Copyright (C) 2005 Dirk Meyer, Jason Tackaberry
#
# First Edition: Dirk Meyer <dmeyer@tzi.de>
# Maintainer:    Dirk Meyer <dmeyer@tzi.de>
#
# Please see the file AUTHORS for a complete list of authors.
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

displays = []

# import X11 support
try:
    from x11 import X11Display, X11Window, EvasX11Window
    displays.append('x11')
except ImportError, e:
    pass

# import Framebuffer support
try:
    from fb import Framebuffer, EvasFramebuffer, PAL_768x576, PAL_800x600, \
         NTSC_640x480, NTSC_768x576, NTSC_800x600
    displays.append('framebuffer')
except ImportError, e:
    pass

# import DirectFB support
try:
    from dfb import EvasDirectFB
    displays.append('directfb')
except ImportError, e:
    pass

# import SDL support
try:
    from sdl import PygameDisplay
    displays.append('sdl')
except ImportError, e:
    pass

