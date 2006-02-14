# -*- coding: iso-8859-1 -*-
# -----------------------------------------------------------------------------
# rss.py - Rss parser
# -----------------------------------------------------------------------------
# $Id$
#
# Notes:
#    Uses feedparser by Mark Pilgrim <http://diveintomark.org/>
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
from cStringIO import StringIO

# webinfo module
from kaa.webinfo.httpreader import HTTPReader
from kaa.webinfo.lib.feedparser import parse


class RssGrabber(HTTPReader):
    """
    This is just a thin layer above the feedparser to accommodate
    our needs for notifying the main loop. It does not return an
    item, only the raw dicts from feedparser. For more information
    on how to use it, ckeck lib/feedparser.
    """
    def __init__(self):
        HTTPReader.__init__(self)


    def _handle_result_threaded(self, output):
        # Use feedparser to parse the results.
        # PS: This seems to take a lot of time
        # (~1.3s on my 2800+), if anyone knows
        # a good implementation which takes as
        # many formats as feedparser, but is
        # quicker, please let me know.
        return parse(output)


    def search(self, rss_url):
        """
        Gets an RSS feed.
        I might actually ditch this method and use get() directly.
        """
        self.get(rss_url)

