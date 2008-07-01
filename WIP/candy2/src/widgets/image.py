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

__all__ = [ 'Image', 'Thumbnail' ]

# python imports
import logging
import os

# clutter imports
import gtk.gdk

# kaa.candy imports imports
from .. import config, threaded
import core

class Image(core.Texture):
    """
    Image widget based on a filename.
    """
    candyxml_name = 'image'
    context_sensitive = True

    def __init__(self, pos, size, filename, context=None):
        """
        @param pos: (x,y) position of the widget or None
        @param size: (width,height) geometry of the widget or None.
        @param filename: filename of the image. If the image is not found
            config.imagepath will be searched for the image. If the filename
            starts with C{$} the filename will be searched in the context.
        @param context: the context the widget is created in
        @todo: add keep aspect
        """
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
        @param name: image filename without path
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


class Thumbnail(Image):
    """
    Widget showing a kaa.beacon.Thumbnail
    """
    candyxml_name = 'thumbnail'
    
    def __init__(self, pos, size, thumbnail, context=None):
        """
        @param pos: (x,y) position of the widget or None
        @param size: (width,height) geometry of the widget or None.
        @param thumbnail: kaa.beacon.Thumbnail object or a string which points
            to the Thumbnail object in the context.
        @param context: the context the widget is created in
        @todo: add default image
        """
        super(Thumbnail, self).__init__(pos, size, None, context)
        self._thumbnail = eval(thumbnail, context)
        self.set_dependency(thumbnail)
        if self._thumbnail.exists():
            return self._show_thumbnail()
        # create thumbnail; be carefull with threads
        self._thumbnail.create().connect_weak_once(self._show_thumbnail)

    @threaded()
    def _show_thumbnail(self):
        """
        Callback to render the thumbnail to the texture.
        @todo: add thumbnail update based on beacon mtime
        """
        if not self._thumbnail.is_failed():
            print self._thumbnail.get()
            self.set_pixbuf(gtk.gdk.pixbuf_new_from_file(self._thumbnail.get()))
        
    @classmethod
    def candyxml_parse(cls, element):
        """
        Parse the candyxml element for parameter to create the widget. Example::
          <thumbnail x='10' y='10' width='100' height='100' thumbnail='thumb'/>
        The thumbnail parameter must be a string that will be evaluated based
        on the given context.
        """
        return core.Texture.candyxml_parse(element).update(
            thumbnail=element.thumbnail)

        
# register widgets to candyxml
Image.candyxml_register()
Thumbnail.candyxml_register()
