# -*- coding: iso-8859-1 -*-
# -----------------------------------------------------------------------------
# image.py - Image Widget
# -----------------------------------------------------------------------------
# $Id$
#
# -----------------------------------------------------------------------------
# kaa-candy - Third generation Canvas System using Clutter as backend
# Copyright (C) 2008-2009 Dirk Meyer, Jason Tackaberry
#
# First Version: Dirk Meyer <dischi@freevo.org>
# Maintainer:    Dirk Meyer <dischi@freevo.org>
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

__all__ = [ 'Imlib2Texture', 'CairoTexture', 'Image', 'Thumbnail' ]

# python imports
import os
import sys
import hashlib
import logging

# kaa imports
import kaa.net.url
from kaa.utils import property

# kaa.candy imports imports
from .. import config, backend
from widget import Widget

# get logging object
log = logging.getLogger('kaa.candy')

# create thread pool for image loading
if 'sphinx' not in sys.modules:
    kaa.register_thread_pool('candy.image', kaa.ThreadPool())

class Imlib2Texture(Widget):
    """
    Clutter Texture widget.
    """

    __keep_aspect = False
    __failed_image = False
    async = False

    _imageloader = kaa.ThreadPoolCallable('candy.image', kaa.imlib2.Image)

    def __init__(self, pos=None, size=None, context=None):
        """
        Simple clutter.Texture widget

        @param pos: (x,y) position of the widget or None
        @param size: (width,height) geometry of the widget or None.
        @param context: the context the widget is created in
        """
        super(Imlib2Texture, self).__init__(pos, size, context)
        self._imagedata = None

    @property
    def keep_aspect(self):
        return self.__keep_aspect

    @keep_aspect.setter
    def keep_aspect(self, keep_aspect):
        self.__keep_aspect = keep_aspect
        self._queue_rendering()
        self._queue_sync_layout()
        self._queue_sync_properties('size')

    def set_image(self, image):
        """
        Set kaa.imlib2.Image. The image will be set to the clutter.Texture
        when _clutter_render is called next.

        @param image: kaa.imlib2.Image or path name
        """
        if image and not isinstance(image, kaa.imlib2.Image):
            if self.async:
                return self._imageloader(image).connect(self.set_image)
            image = kaa.imlib2.Image(image)
        self._imagedata = image
        self._queue_rendering()
        if self.__keep_aspect:
            self._queue_sync_layout()
        self._queue_sync_properties('imagedata')

    def has_image(self):
        """
        Returns if the widget has an image set
        """
        return self._imagedata is not None

    def _clutter_render(self):
        """
        Render the widget
        """
        if self._obj is None:
            self._obj = backend.Texture()
            self._obj.show()
            self._clutter_set_obj_size()
            if not self._imagedata:
                self.__failed_image = True
                self._obj.hide()
        if 'size' in self._sync_properties or self.__keep_aspect:
            width, height = self.inner_width, self.inner_height
            if self.__keep_aspect and self._imagedata:
                aspect = float(self._imagedata.width) / self._imagedata.height
                if int(height * aspect) > width:
                    height = int(width / aspect)
                else:
                    width = int(height * aspect)
            self._clutter_set_obj_size(width, height)
        if 'imagedata' in self._sync_properties:
            if self._imagedata:
                if self.__failed_image:
                    self.__failed_image = False
                    self._obj.show()
                width, height = self._imagedata.size
                self._obj.set_from_rgb_data(self._imagedata.get_raw_data(), True,
                     width, height, width*4, 4, backend.TEXTURE_RGB_FLAG_BGR)
            elif not self.__failed_image:
                self.__failed_image = True
                self._obj.hide()


class CairoTexture(Widget):
    """
    Cairo based Texture widget.
    """


    def _clutter_render(self):
        """
        Render the widget
        """
        if self._obj is None:
            self._obj = backend.CairoTexture(int(self.inner_width), int(self.inner_height))
            self._obj.set_size(int(self.inner_width), int(self.inner_height))
            self._obj.show()
            return
        if 'size' in self._sync_properties:
            self._obj.set_size(int(self.inner_width), int(self.inner_height))
            if self._clutter_resize_surface:
                w, h = self._obj.get_size()
                self._obj.set_surface_size(int(w), int(h))
        self._obj.clear()


class Image(Imlib2Texture):
    """
    Image widget based on a filename.
    """
    candyxml_name = 'image'
    context_sensitive = True

    _downloads = {}

    def __init__(self, pos, size, url=None, context=None):
        """
        Create the Image

        @param pos: (x,y) position of the widget or None
        @param size: (width,height) geometry of the widget
        @param url: filename or url of the image. If the image is not found
            config.imagepath will be searched for the image. If the url
            starts with C{$} the url will be searched in the context.
        @param context: the context the widget is created in
        @todo: add default image if not found or still fetched
        @todo: better url handling (see FIXME in the code)
        """
        super(Image, self).__init__(pos, size, context)
        if not url:
            return
        if url.startswith('$'):
            # variable from the context, e.g. $varname
            self.add_dependency(url)
            url = self.context.get(url)
            if not url:
                return
        if isinstance(url, kaa.imlib2.Image):
            self.set_image(url)
            return
        if url.startswith('http://'):
            # remote image, create local cachefile
            # FIXME: how to handle updates on the remote side?
            base = hashlib.md5(url).hexdigest() + os.path.splitext(url)[1]
            cachefile = kaa.tempfile('candy-images/' + base)
            if not os.path.isfile(cachefile):
                # Download the image
                # FIXME: errors will be dropped
                # FIXME: support other remote sources
                # FIXME: use one thread (jobserver) for all downloads
                #  or at least a max number of threads to make the individual
                #  image loading faster
                if not cachefile in self._downloads:
                    tmpfile = kaa.tempfile('candy-images/.' + base)
                    c = kaa.net.url.fetch(url, cachefile, tmpfile)
                    self._downloads[cachefile] = c
                self._downloads[cachefile].connect_weak_once(self._fetched, cachefile)
                return
            # use cachefile as image
            url = cachefile
        if not url.startswith('/'):
            url = self._get_image_by_url(url)
            if not url:
                return
        self.set_image(url)

    def _fetched(self, status, cachefile):
        """
        Callback for HTTP GET result. The image should be in the cachefile.
        """
        if cachefile in self._downloads:
            del self._downloads[cachefile]
        self.set_image(cachefile)

    def _get_image_by_url(self, name):
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
        Parse the candyxml element for parameter to create the widget. Example::
          <image x='10' y='10' width='200' height='100' filename='image.jpg'/>
          <image width='200' height='100' url='http://www.exapmple.com/image.jpg'/>
        """
        return super(Image, cls).candyxml_parse(element).update(
            url=element.url or element.filename)


class Thumbnail(Image):
    """
    Widget showing a kaa.beacon.Thumbnail
    """
    candyxml_name = 'thumbnail'

    def __init__(self, pos, size, thumbnail=None, default=None, context=None):
        """
        Create the Thumbnail widget

        @param pos: (x,y) position of the widget or None
        @param size: (width,height) geometry of the widget
        @param thumbnail: kaa.beacon.Thumbnail object or a string which points
            to the Thumbnail object in the context.
        @param context: the context the widget is created in
        """
        super(Thumbnail, self).__init__(pos, size, context=context)
        self.keep_aspect = True
        self.set_thumbnail(thumbnail, default)

    def set_thumbnail(self, thumbnail, default=None):
        if isinstance(thumbnail, (str, unicode)):
            # get thumbnail from context
            # FIXME: make this dynamic
            self.add_dependency(thumbnail)
            thumbnail = self.context.get(thumbnail)
        item = None
        if hasattr(thumbnail, 'scan'):
            # FIXME: bad detection
            # thumbnail is a kaa.beacon.Item
            item, thumbnail = thumbnail, thumbnail.get('thumbnail')
        self._thumbnail = thumbnail
        if self._thumbnail is not None:
            # show thumbnail
            self._show_thumbnail(force=True)
            return
        if default and not default.startswith('/'):
            default = self._get_image_by_url(default)
        if default:
            self.set_image(default)
        if item is not None and not item.scanned:
            scanning = item.scan()
            if scanning:
                scanning.connect_weak_once(self._beacon_update, item)

    def _beacon_update(self, changes, item):
        self._thumbnail = item.get('thumbnail')
        if self._thumbnail is not None:
            return self._show_thumbnail(force=True)

    def _show_thumbnail(self, force=False):
        """
        Callback to render the thumbnail to the texture.
        @todo: add thumbnail update based on beacon mtime
        @todo: try to force large thumbnails
        """
        image = self._thumbnail.image
        if image:
            self.set_image(image)
        elif self._thumbnail.failed:
            return False
        if force and self._thumbnail.needs_update:
            # Create thumbnail; This object will hold a reference to the
            # beacon.Thumbnail object and uses high priority. Since we
            # only connect weak to the result we loose the thumbnail object
            # when this widget is removed which will reduce the priority
            # to low. This is exactly what we want. The create will be
            # scheduled in the mainloop but since we do not wait it is ok.
            self._thumbnail.create(self._thumbnail.PRIORITY_HIGH).\
                connect_weak_once(self._show_thumbnail)

    @classmethod
    def candyxml_parse(cls, element):
        """
        Parse the candyxml element for parameter to create the widget. Example::
          <thumbnail x='10' y='10' width='100' height='100' thumbnail='thumb'/>
        The thumbnail parameter must be a string that will be evaluated based
        on the given context.
        """
        return Imlib2Texture.candyxml_parse(element).update(
            thumbnail=element.thumbnail, default=element.default)
