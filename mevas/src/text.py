# -*- coding: iso-8859-1 -*-
# -----------------------------------------------------------------------------
# text.py - Text Canvas
# -----------------------------------------------------------------------------
# $Id$
#
# -----------------------------------------------------------------------------
# kaa-mevas - MeBox Canvas System
# Copyright (C) 2004-2005 Jason Tackaberry <tack@sault.org>
#
# First Edition: Jason Tackaberry <tack@sault.org>
# Maintainer:    Jason Tackaberry <tack@sault.org>
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

__all__ = [ 'CanvasText' ]

# python imports
import types

# mevas imports
import imagelib
from util import *
from image import *

class CanvasText(CanvasImage):

    # TODO: get default font and color from theme or something
    def __init__(self, text = None, font = "arial", size = 24,
                 color = (255,255,255,255)):
        CanvasImage.__init__(self)
        self.fontname = self.size = None

        self.set_font(font, size)
        self.set_color(color)
        self.metrics = None
        if text:
            self.set_text(text, color)

    def __repr__(self):
        text = None
        if hasattr(self, "text"): text=self.text
        return "<CanvasText object at 0x%x: \"%s\">" % (id(self), text)



    def set_color(self, color):
        if not hasattr(self, "color") or color != self.color:
            self.color = color

            # Rerender text in new color
            if hasattr(self, "text"):
                self.set_text(self.text, force = True)


    def set_font(self, font, size = 24):
        try:
            if type(font) in types.StringTypes:
                self.font = imagelib.load_font(font, size)
            else:
                self.font = font
            if hasattr(self, "text") and \
                   (font, size) != (self.fontname, self.size):
                # Need to re-render text with new font and/or size.
                self.set_text(self.text, force = True)
        except IOError:
            print "Font %s/%d failed to load, so using default" % (font, size)
            self.font = imagelib.load_font("arial", 24)

        self.fontname, self.size = self.font.fontname, self.font.size


    def set_text(self, text, color = None, force = False):
        if hasattr(self, "text") and self.text == text and not force:
            return
        self.text = text
        self.metrics = metrics = self.font.get_text_size(text)
        self.new( (metrics[0] + 2, metrics[1]) )
        if not color:
            color = self.color
        self.draw_text(text + " ", (0, 0), font=self.font, color=color)
        self.needs_blitting(True)
        self.queue_paint()

    def get_text(self):
        return self.text

    def get_metrics(self):
        return self.metrics
