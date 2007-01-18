# -*- coding: iso-8859-1 -*-
# -----------------------------------------------------------------------------
# fb.py - Framebuffer Display
# -----------------------------------------------------------------------------
# $Id$
#
# Note: The DirectFB output without evas is crashing. It needs much work, but
# by DirectFB knowledge is close to zero.
#
# -----------------------------------------------------------------------------
# kaa.display - Generic Display Module
# Copyright (C) 2005, 2006 Dirk Meyer, Jason Tackaberry
#
# First Edition: Dirk Meyer <dmeyer@tzi.de>
# Maintainer:    Dirk Meyer <dmeyer@tzi.de>
# Maintainer:    Rob Shortt <rob@tvcentric.com>
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

__all__ = [ 'DirectFB', 'EvasDirectFB' ]

import _DFBmodule as dfb

class _DirectFB(object):
    """
    Base class for DirectFB framebuffer.
    """
    def __init__(self, size, **kwargs):
        # check size, it comes in as a tupple
        # we can't parse tupples with kwargs in the C extention
        dfb.open(size[0], size[1], **kwargs)


    def size(self):
        """
        return the size of the framebuffer.
        """
        return dfb.size()


    def get_id(self):
        """
        Fake id function that does not return a windows id but returns a
        string that would identify this as DirectFB.
        """
        return 'dfb'


    def __del__(self):
        print 'close dfb'
        dfb.close()


class DirectFB(_DirectFB):
    """
    DirectFB framebuffer.
    """
    pass


class EvasDirectFB(_DirectFB):
    """
    Frambuffer using evas for drawing
    The 'mode' argument can either be a size (width, height) matching one of
    the specified framebuffer resolutions, a list for fbset or None. If set to
    None, the current framebuffer size will be used.
    """
    def __init__(self, size, **kwargs):
        _DirectFB.__init__(self, size, **kwargs)
        import kaa.evas
        self._evas = kaa.evas.Evas()
        dfb.new_evas_dfb(self._evas._evas)


    def get_evas(self):
        """
        Return evas object.
        """
        return self._evas


    def __del__(self):
        print 'delete evas object'
        del self._evas
        _DirectFB.__del__(self)
