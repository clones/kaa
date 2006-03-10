# -*- coding: iso-8859-1 -*-
# -----------------------------------------------------------------------------
# fb.py - Framebuffer Display
# -----------------------------------------------------------------------------
# $Id: fb.py 1041 2005-12-27 19:06:37Z dmeyer $
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

__all__ = [ 'EvasDirectFB' ]

import _DFBmodule as dfb

class EvasDirectFB(object):
    """
    Frambuffer using evas for drawing
    The 'mode' argument can either be a size (width, height) matching one of the
    specified framebuffer resolutions, a list for fbset or None. If set to None,
    the current framebuffer size will be used.
    """
    def __init__(self, size):
        import kaa.evas
        dfb.open(size)
        self._evas = kaa.evas.Evas()
        dfb.new_evas_dfb(self._evas._evas)

        
    def size(self):
        """
        return the size of the framebuffer.
        """
        return dfb.size()


    def get_evas(self):
        """
        Return evas object.
        """
        return self._evas


    def __del__(self):
        print 'delete evas object'
        del self._evas
        print 'close dfb'
        dfb.close()

