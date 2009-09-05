# -*- coding: iso-8859-1 -*-
# -----------------------------------------------------------------------------
# themoviedb.py - Access themoviedb.org
# -----------------------------------------------------------------------------
# $Id$
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

__all__ = [ 'MovieDB' ]

# python imports
import os
import re
import xml.sax
import logging
import urllib

# kaa imports
import kaa
import kaa.db
from kaa.saxutils import ElementParser, Element

# get logging object
log = logging.getLogger('webmetadata')

API_SERVER='api.themoviedb.org'

REMOVE_FROM_SEARCH = []

IMDB_REGEXP = re.compile('http://[a-z]+.imdb.[a-z]+/[a-z/]+([0-9]+)')
IMAGE_REGEXP = re.compile('.*/([0-9]*)/')

class Movie(object):
    """
    Movie Information.

    The following attributes are available: title, plot, year, images
    """
    class Image(object):
        url = thumbnail = ''

        @kaa.threaded()
        def fetch(self):
            return urllib.urlopen(self.url).read()

    def __init__(self, data):
        self._data = data
        self.title = data['title']
        self.plot = data.get('short_overview')
        self.year = None
        if data.get('release') and len(data.get('release').split('-')) == 3:
            self.year = data.get('release').split('-')[0]
        # FIXME: add more stuff. The details also include new
        # information Maybe a self.update() function could be used to
        # move from search result to detailed info

    def _images(self, tagname, size):
        result = []
        for urlsize, url in self._data[tagname]:
            m = IMAGE_REGEXP.match(url)
            i = int(m.groups()[0])
            for r in result:
                if r._id == i:
                    break
            else:
                r = Movie.Image()
                r._id = i
                result.append(r)
            if not r.url:
                r.url = url
            if urlsize == 'thumb':
                r.thumbnail = url
            if urlsize == size:
                r.url = url
        return result

    def items(self):
        return self._data.items()

    @property
    def images(self):
        return self._images('poster', 'mid')

    @property
    def backdrop(self):
        return self._images('backdrop', 'original')


class Filename(object):

    available = False

    def __init__(self, moviedb, apikey, filename, parsed):
        self.filename = filename
        self._db = moviedb
        self._apikey = apikey
        self._searchdata = parsed
        self._movie = None
        if parsed[2]:
            movie = self._db.query(imdb=unicode(parsed[2]), type='movie')
            if movie:
                self._movie = Movie(movie[0]['data'])
                self.available = True

    @kaa.threaded()
    def _fetch_and_parse(self, url):
        results = []
        def handle(element):
            if not element.content:
                data = dict(categories=[], actor=[], director=[], backdrop=[], poster=[])
                for child in element:
                    if child.content:
                        if child.tagname in ('backdrop', 'poster'):
                            data[child.tagname].append((child.size, child.content))
                            continue
                        data[child.tagname] = child.content
                        continue
                    if child.tagname == 'categories':
                        for c in child:
                            data['categories'].append(c.name.content)
                        continue
                    if child.tagname == 'people':
                        for p in child:
                            if p.job in ('director', 'actor'):
                                data[p.job].append(p.name.content)
                        continue
                results.append(Movie(data))
        e = ElementParser('movie')
        e.handle = handle
        parser = xml.sax.make_parser()
        parser.setContentHandler(e)
        parser.parse(url)
        return results

    def search(self, string=None):
        if not string:
            string = self._searchdata[0]
        url = 'http://%s/2.0/Movie.search?%s' % (API_SERVER, urllib.urlencode({'title': string.strip(), 'api_key': self._apikey}))
        return self._fetch_and_parse(url)

    @kaa.coroutine()
    def fetch(self, id=None):
        if self._movie:
            yield self._movie
        if id is None and self._searchdata[2]:
            id = self._searchdata[2]
        if id is None:
            yield None
        if isinstance(id, (str, unicode)) and id.startswith('tt'):
            url = 'http://%s/2.0/Movie.imdbLookup?%s' % (API_SERVER, urllib.urlencode({'imdb_id': id, 'api_key': self._apikey}))
            result = yield self._fetch_and_parse(url)
            if not result:
                yield None
            id = result[0]._data['id']
        url = 'http://%s/2.0/Movie.getInfo?%s' % (API_SERVER, urllib.urlencode({'id': id, 'api_key': self._apikey}))
        result = yield self._fetch_and_parse(url)
        if not result:
            yield None
        movie = result[0]
        self._db.add('movie', moviedb=int(movie._data['id']), title=movie.title, imdb=movie._data.get('imdb', ''), data=movie._data)
        yield movie

    def __getattr__(self, attr):
        if not self._movie:
            raise AttributeError('%s is no invalid' % self.filename)
        return getattr(self._movie, attr)


class MovieDB(object):

    def __init__(self, database, apikey='21dfe870a9244b78b4ad0d4783251c63'):
        self._apikey = apikey
        # set up the database and the version file
        if not os.path.exists(os.path.dirname(database)):
            os.makedirs(os.path.dirname(database))
        self._db = kaa.db.Database(database)
        self._db.register_object_type_attrs("movie",
            moviedb = (int, kaa.db.ATTR_SEARCHABLE),
            imdb = (unicode, kaa.db.ATTR_SEARCHABLE),
            title = (unicode, kaa.db.ATTR_SEARCHABLE),
            data = (dict, kaa.db.ATTR_SIMPLE),
        )

    def from_filename(self, filename):
        """
        """
        search = ''
        imdb = None
        nfo = os.path.splitext(filename)[0] + '.nfo'
        if os.path.exists(nfo):
            match = IMDB_REGEXP.search(open(nfo).read())
            if match:
                imdb = 'tt' + match.groups()[0]
        for part in re.split('[\._ -]', os.path.splitext(os.path.basename(filename))[0]):
            if part.lower() in REMOVE_FROM_SEARCH:
                break
            try:
                if len(search) and int(part) > 1900 and int(part) < 2100:
                    return Filename(self._db, self._apikey, filename, (search.strip(), int(part), imdb))
            except ValueError:
                pass
            search += ' ' + part
        return Filename(self._db, self._apikey, filename, (search.strip(), None, imdb))
