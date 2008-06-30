# -*- coding: iso-8859-1 -*-
# -----------------------------------------------------------------------------
# image.py - Image Widget
# -----------------------------------------------------------------------------
# $Id$
#
# -----------------------------------------------------------------------------
# kaa-candy - Third generation Canvas System using Clutter as backend
# Copyright (C) 2008 Dirk Meyer, Jason Tackaberry
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

# python imports
import logging
import os

# clutter imports
import gtk.gdk

# kaa.candy imports imports
from .. import config
import core

imagedir = None

class Image(core.Texture):
    """
    Image widget based on a filename.
    """
    candyxml_name = 'image'
    context_sensitive = True

    def __init__(self, pos, size, filename, context=None):
        super(Image, self).__init__(pos, size, context)
        if filename and filename.startswith('$'):
            self.set_dependency(filename[1:])
            filename = eval(filename[1:], context)
        if filename and not filename.startswith('/'):
            filename = self._get_image(filename)
        if filename:
            self.set_pixbuf(gtk.gdk.pixbuf_new_from_file(filename))

    def _get_image(self, name):
        """
        Helper function to get the full path of the image.
        """
        for path in config.imagepath:
            filename = os.path.join(path, name)
            if os.path.isfile(filename):
                return filename
        return None

    @classmethod
    def candyxml_parse(cls, element):
        """
        Parse the XML element for parameter to create the widget.
        """
        return super(Image, cls).candyxml_parse(element).update(
            filename=element.filename)


# register widget to candyxml
Image.candyxml_register()
