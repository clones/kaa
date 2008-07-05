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
import os
import md5
import logging

# clutter imports
import gtk.gdk

# kaa imports
import kaa.net.url

# kaa.candy imports imports
from .. import config, threaded
import core

# get logging object
log = logging.getLogger('kaa.candy')

class Image(core.Texture):
    """
    Image widget based on a filename.
    """
    candyxml_name = 'image'
    context_sensitive = True

    _downloads = {}
    
    def __init__(self, pos, size, url, context=None):
        """
        @param pos: (x,y) position of the widget or None
        @param size: (width,height) geometry of the widget or None.
        @param url: filename or url of the image. If the image is not found
            config.imagepath will be searched for the image. If the url
            starts with C{$} the url will be searched in the context.
        @param context: the context the widget is created in
        @todo: add keep aspect; aspect ratio is a property on clutter 0.7 so we wait.
        @todo: add default image if not found or still fetched
        @todo: better url handling (see FIXME in the code)
        """
        super(Image, self).__init__(pos, size, context)
        if not url:
            return
        if url.startswith('$'):
            # variable from the context, e.g. $varname
            self.set_dependency(url[1:])
            url = eval(url[1:], context)
            if not url:
                return
        if url.startswith('http://'):
            # remote image, create local cachefile
            # FIXME: how to handle updates on the remote side?
            base = md5.md5(url).hexdigest() + os.path.splitext(url)[1]
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
                    self._downloads[cachefile] = kaa.net.url.fetch(url, cachefile, tmpfile)
                self._downloads[cachefile].connect_weak_once(self._fetched, cachefile)
                return
            # use cachefile as image
            url = cachefile
        if not url.startswith('/'):
            url = self._get_image(url)
            if not url:
                return
        # load the image to the texture
        self.set_pixbuf(gtk.gdk.pixbuf_new_from_file(url))

    @threaded()
    def _fetched(self, status, cachefile):
        """
        Callback for HTTP GET result. The image should be in the cachefile.
        """
        if cachefile in self._downloads:
            del self._downloads[cachefile]
        try:
            self.set_pixbuf(gtk.gdk.pixbuf_new_from_file(cachefile))
        except Exception, e:
            log.exception('bad image: %s' % cachefile)

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
        if isinstance(thumbnail, (str, unicode)):
            # get thumbnail from context
            self.set_dependency(thumbnail)
            thumbnail = eval(thumbnail, context)
        self._thumbnail = thumbnail
        if self._thumbnail is not None and self._thumbnail.exists():
            # show thumbnail
            return self._show_thumbnail()
        if self._thumbnail is not None:
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
