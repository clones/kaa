# -*- coding: iso-8859-1 -*-
# -----------------------------------------------------------------------------
# bmovlcanvas.py - output canvas for bmovl
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

# python imports
import os

# mevas imports
import kaa.mevas.rect as rect
from kaa.mevas import imagelib

# displays imports
from bitmapcanvas import *


fifo_counter = 0

def create_fifo():
    """
    return a unique fifo name
    """
    global fifo_counter
    fifo = '/tmp/bmovl-%s-%s' % (os.getpid(), fifo_counter)
    fifo_counter += 1
    if os.path.exists(fifo):
        os.unlink(fifo)
    os.mkfifo(fifo)
    return fifo


class BmovlCanvas(BitmapCanvas):

    def __init__(self, size, fifo = None):
        if fifo:
            self.__fname = fifo
        self.open_fifo()
        self.bmovl_visible = True
        self.send('SHOW\n')
        super(BmovlCanvas, self).__init__(size, preserve_alpha = True)
        self._update_rect = None


    def open_fifo(self):
        self.fifo = os.open(self.get_fname(), os.O_RDWR, os.O_NONBLOCK)


    def close_fifo(self):
        if self.fifo:
            try:
                os.close(self.fifo)
            except OSError:
                self.fifo = None
        if os.path.exists(self.get_fname()):
            os.unlink(self.get_fname())


    def get_fname(self):
        """
        return fifo filename
        """
        try:
            return self.__fname
        except AttributeError:
            pass
        self.__fname = create_fifo()
        return self.__fname


    def send(self, msg):
        try:
            os.write(self.fifo, msg)
            return True
        except (IOError, OSError):
            return False

    def has_visible_child(self):
        for c in self.children:
            if c.visible and c.get_alpha():
                return True
        return False


    def _update_end(self, object = None):
        if not self._update_rect:
            return
        if not self.fifo:
            return

        if self.bmovl_visible and not self.has_visible_child():
            self.send('HIDE\n')
            self.send('CLEAR %s %s 0 0\n' % \
                  (self.width, self.height))
            self.bmovl_visible = False
            return

        # get update rect
        pos, size = self._update_rect
        # increase update rect because mplayer sometimes draws outside
        pos = (max(0, pos[0] - 2), max(pos[1] - 2, 0))
        size = (min(size[0] + 4, self.width),
            min(size[1] + 4, self.height))

        img = imagelib.crop(self._backing_store, pos, size)
        self.send('RGBA32 %d %d %d %d %d %d\n' % \
              (size[0], size[1], pos[0], pos[1], 0, 0))
        self.send(str(img.get_raw_data('RGBA')))
        self._update_rect = None

        if not self.bmovl_visible and self.has_visible_child():
            self.send('SHOW\n')
            self.bmovl_visible = True


    def _blit(self, img, r):
        if self._update_rect:
            self._update_rect = rect.union(r, self._update_rect)
        else:
            self._update_rect = r
