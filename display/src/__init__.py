# -*- coding: iso-8859-1 -*-
# -----------------------------------------------------------------------------
# display - Interface to the display code
# -----------------------------------------------------------------------------
# $Id$
#
# -----------------------------------------------------------------------------
# kaa.display - Generic Display Module
# Copyright (C) 2005, 2006 Dirk Meyer, Jason Tackaberry
#
# First Edition: Dirk Meyer <dmeyer@tzi.de>
# Maintainer:    Dirk Meyer <dmeyer@tzi.de>
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
    from dfb import DirectFB, EvasDirectFB
    displays.append('directfb')
except ImportError, e:
    pass

# import SDL support
try:
    from sdl import PygameDisplay
    displays.append('sdl')
except ImportError, e:
    pass

# import LCDProc support
from lcdproc import LCD
