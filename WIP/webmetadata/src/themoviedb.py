# -*- coding: iso-8859-1 -*-
# -----------------------------------------------------------------------------
# themoviedb.py - Access themoviedb.org
# -----------------------------------------------------------------------------
# $Id: tvdb.py 3955 2009-03-24 13:05:32Z dmeyer $
#
# -----------------------------------------------------------------------------
# kaa.webmetadata - Receive Metadata from the Web
# Copyright (C) 2009 Dirk Meyer
#
# First Edition: Dirk Meyer <dischi@freevo.org>
# Maintainer:    Dirk Meyer <dischi@freevo.org>
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

__all__ = [ 'Movie', 'search', 'get' ]

# python imports
import urllib
import re
import xml.sax
import logging

# kaa imports
import kaa
from kaa.saxutils import ElementParser

# get logging object
log = logging.getLogger('webmetadata')

# API key for themoviedb API access. We do not have a key for kaa
# yet. Maybe the request got lost.
API_KEY=''

API_SERVER='api.themoviedb.org'


class Movie(object):
    """
    Movie Information.

    The following attributes are available: title, plot, year, images
    """
    class Image(object):
        url = thumbnail = ''

    plot = year = None

    def __init__(self, element):
        self._element = element
        self.title = element.title.content
        if element.short_overview:
            self.plot = element.short_overview.content
        if element.release and len(element.release.content.split('-')) == 3:
            self.year = element.release.content.split('-')[0]
        # FIXME: add more stuff. The details also include new
        # information Maybe a self.update() function could be used to
        # move from search result to detailed info

    def _images(self, tagname, large):
        result = []
        for p in self._element.get_children(tagname):
            m = re.match('http://www.themoviedb.org/image/[^/]*/([0-9]*)/', p.content)
            if not m:
                log.warning('error in image check: %s', p.content)
                continue
            i = int(m.groups()[0])
            for r in result:
                if r._id == i:
                    break
            else:
                r = Movie.Image()
                r._id = i
                result.append(r)
            if not r.url:
                r.url = p.content
            if p.size == 'thumb':
                r.thumbnail = p.content
            if p.size == large:
                r.url = p.content
        return result

    @property
    def images(self):
        return self._images('poster', 'mid')

    @property
    def backdrop(self):
        return self._images('backdrop', 'original')


@kaa.threaded()
def _parse(url):
    results = []
    def handle(element):
        if not element.content:
            results.append(Movie(element))
    e = ElementParser('movie')
    e.handle = handle
    parser = xml.sax.make_parser()
    parser.setContentHandler(e)
    parser.parse(url)
    return results

def search(string):
    if not API_KEY:
        raise RuntimeError('API_KEY not given')
    url = 'http://%s/2.0/Movie.search?%s' % (API_SERVER, urllib.urlencode({'title': string.strip(), 'api_key': API_KEY}))
    return _parse(url)

@kaa.coroutine()
def get(id):
    if not API_KEY:
        raise RuntimeError('API_KEY not given')
    if isinstance(id, (str, unicode)) and id.startswith('tt'):
        url = 'http://%s/2.0/Movie.imdbLookup?%s' % (API_SERVER, urllib.urlencode({'imdb_id': id, 'api_key': API_KEY}))
    else:
        url = 'http://%s/2.0/Movie.getInfo?%s' % (API_SERVER, urllib.urlencode({'id': id, 'api_key': API_KEY}))
    result = yield _parse(url)
    if not result:
        yield None
    yield result[0]
