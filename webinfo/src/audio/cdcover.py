# -*- coding: iso-8859-1 -*-
# -----------------------------------------------------------------------------
# cdcover.py - Fetches covers from amazon
# -----------------------------------------------------------------------------
# $Id$
#
# -----------------------------------------------------------------------------
# kaa-webinfo - Python module for gathering information from the web
# Copyright (C) 2002-2005 Viggo Fredriksen, Dirk Meyer, et al.
#
# First Edition: Viggo Fredriksen <viggo@katatonic.org>
# Maintainer:    Viggo Fredriksen <viggo@katatonic.org>
#
# Please see the file doc/CREDITS for a complete list of authors.
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

# python modules
from xml.dom import minidom
import urllib2

# kaa modules
from kaa.notifier import Signal
import kaa.imlib2

# webinfo modules
from kaa.webinfo.httpreader import HTTPReader
from kaa.webinfo.grabberitem import GrabberItem

# amazon module
import kaa.webinfo.lib.amazon as amazon


class CDCoverItem(GrabberItem):
    """
    Class representing the result
    """
    cover        = None
    release_date = None
    album        = None
    artist       = None
    tracks       = []


class CDCoverGrabber(HTTPReader):
    def __init__(self, amazon_license=None):
        HTTPReader.__init__(self)
        self.show_progress = False
        
        # configure the license
        self.amazon_license = amazon_license


    def search(self, search_type, keyword, product_line, type="heavy", page=None):
        key = amazon.getLicense(self.amazon_license)
        url = amazon.buildURL(search_type, keyword, product_line, type, page, key)
        self.status_callback('searching')
        self.get(url)

        
    def search_by_artist(self, artist, product_line="music", type="heavy", page=1):
        if product_line not in ("music", "classical"):
            raise amazon.AmazonError, "product_line must be in ('music', 'classical')"
        return self.search("ArtistSearch", artist, product_line, type, page)


    def search_by_keyword(self, keyword, product_line="books", type="heavy", page=1):
        return self.search("KeywordSearch", keyword, product_line, type, page)


    def _handle_result_threaded(self, output):
        """
        Finished receiving results
        """
        xmldoc = minidom.parse(output)
        data = amazon.unmarshal(xmldoc).ProductInfo
        if hasattr(data, 'ErrorMsg'):
            output.close()
            raise amazon.AmazonError, data.ErrorMsg

        items = []

        for cover in data.Details:
            item = CDCoverItem()

            self.progress_callback(data.Details.index(cover) + 1, len(data.Details))
            self.status_callback('getting cover "%s"' % cover.ProductName)
            for url in cover.ImageUrlLarge, cover.ImageUrlMedium, \
                    cover.ImageUrlLarge.replace('.01.', '.03.'):
                try:
                    idata = urllib2.urlopen(url)
                    if idata.info()['Content-Length'] == '807':
                        idata.close()
                        continue
                    image = kaa.imlib2.open_from_memory(idata.read())
                    image = image.crop((2,2), (image.width-4, image.height-4))
                    item.cover = image
                    idata.close()
                    break
                except urllib2.HTTPError:
                    # Amazon returned a 404 or bad image
                    pass
                except:
                    continue
                    
            else:
                # no image found
                pass

            if hasattr(cover, 'ReleaseDate'):
                item.release_date = cover.ReleaseDate
            if hasattr(cover, 'ProductName'):
                item.album = cover.ProductName
            if hasattr(cover, 'Artists'):
                if isinstance(cover.Artists.Artist, list):
                    item.artist = u', '.join(cover.Artists.Artist)
                else:
                    item.artist = cover.Artists.Artist
                
            if hasattr(cover, 'Tracks'):
                item.tracks = cover.Tracks.Track

            items.append(item)

        return items
