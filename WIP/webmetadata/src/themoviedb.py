# -*- coding: iso-8859-1 -*-
# -----------------------------------------------------------------------------
# themoviedb.py - Access themoviedb.org
# -----------------------------------------------------------------------------
# $Id$
#
# -----------------------------------------------------------------------------
# kaa.webmetadata - Receive Metadata from the Web
# Copyright (C) 2009-2011 Dirk Meyer
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
import socket
import urllib
import urllib2

# kaa imports
import kaa
import kaa.db
from kaa.saxutils import ElementParser, Element

import core

# get logging object
log = logging.getLogger('webmetadata')

API_SERVER='api.themoviedb.org'

REMOVE_FROM_SEARCH = []
WORKER_THREAD = 'WEBMETADATA'

IMDB_REGEXP = re.compile('http://[a-z\.]*imdb.[a-z]+/[a-z/]+([0-9]+)')
IMAGE_REGEXP = re.compile('.*/([0-9]*)/')

class Movie(core.Movie):
    """
    Movie Information.
    """
    def __init__(self, data):
        self._data = data
        self.id = 'themoviedb:%s' % data['id']
        self.title = data['name']
        self.overview = data.get('overview')
        self.rating = data.get('rating')
        self.runtime = data.get('runtime')
        self.year = None
        if data.get('released') and len(data.get('released').split('-')) == 3:
            self.year = data.get('released').split('-')[0]
        # FIXME: add more stuff. The details also include new
        # information Maybe a self.update() function could be used to
        # move from search result to detailed info

    def _images(self, tagname, size):
        result = []
        for id, image in self._data[tagname].items():
            i = core.Image()
            for size in (size, 'mid', 'original', 'cover'):
                if size in image:
                    i.url = image[size]
                    break
            i.thumbnail = image.get('thumb')
            result.append(i)
        return result

    @property
    def posters(self):
        return self._images('poster', 'mid')

    @property
    def images(self):
        return self._images('backdrop', 'original')



class MovieDB(core.Database):

    scheme = 'themoviedb:'

    def __init__(self, database, apikey='21dfe870a9244b78b4ad0d4783251c63'):
        super(MovieDB, self).__init__(database)
        self._apikey = apikey
        self._db.register_object_type_attrs("metadata",
            metadata = (dict, kaa.db.ATTR_SIMPLE),
        )
        self._db.register_object_type_attrs("movie",
            moviedb = (int, kaa.db.ATTR_SEARCHABLE),
            imdb = (unicode, kaa.db.ATTR_SEARCHABLE),
            title = (unicode, kaa.db.ATTR_SEARCHABLE),
            data = (dict, kaa.db.ATTR_SIMPLE),
        )
        self._db.register_object_type_attrs("hash",
            moviedb = (int, kaa.db.ATTR_SIMPLE),
            value = (unicode, kaa.db.ATTR_SEARCHABLE),
        )
        if not self._db.query(type='metadata'):
            self._db.add('metadata', metadata={})

    @kaa.threaded(WORKER_THREAD)
    def download(self, url):
        results = []
        def handle(element):
            if not element.content:
                data = dict(categories=[], backdrop={}, poster={})
                for child in element:
                    if child.tagname == 'categories' and child.type == 'genre':
                        data['categories'].append(child.name)
                    elif child.tagname == 'images':
                        for image in child:
                            if not image.type  in ('backdrop', 'poster'):
                                continue
                            if not image.id in data[image.type]:
                                data[image.type][image.id] = {}
                            data[image.type][image.id][image.size] = image.url
                    elif child.content:
                        data[child.tagname] = child.content
                results.append(Movie(data))
        e = ElementParser('movie')
        e.handle = handle
        parser = xml.sax.make_parser()
        parser.setContentHandler(e)
        try:
            parser.parse(urllib2.urlopen(url, timeout=10))
        except Exception, e:
            log.exception('download/parse error')
            return []
        return results

    def parse(self, filename, metadata):
        if metadata.get('hash'):
            data = self._db.query(type='hash', value=u'%s|%s' % \
                                      (metadata.get('hash'), os.path.getsize(filename)))
            if data:
                data = self._db.query(type='movie', moviedb=data[0]['moviedb'])
                return Movie(data[0]['data'])
        nfo = os.path.splitext(filename)[0] + '.nfo'
        if os.path.exists(nfo):
            match = IMDB_REGEXP.search(open(nfo).read())
            if match:
                data = self._db.query(type='movie', imdb=u'tt' + match.groups()[0])
                if data:
                    return Movie(data[0]['data'])
        return None

    @kaa.coroutine()
    def search(self, filename, metadata):
        apicall = 'http://api.themoviedb.org/2.1/%s/en/xml/' + self._apikey + '/%s'
        result = []
        # No idea if this code is working. I have no working files
        # if metadata.hash:
        #     url = apicall % ('Media.getInfo', '%s/%s' % (metadata.hash, os.path.getsize(filename)))
        #     result = yield self.download(url)
        nfo = os.path.splitext(filename)[0] + '.nfo'
        if os.path.exists(nfo) and not result:
            match = IMDB_REGEXP.search(open(nfo).read())
            if match:
                url = apicall % ('Movie.imdbLookup', 'tt' + match.groups()[0])
            result = yield self.download(url)
        if metadata.get('title') and not result:
            url = apicall % ('Movie.search', metadata.get('title'))
            result = yield self.download(url)
        # searching based on the filename is bad unless we have some
        # logic what parts we need.
        if not result and False:
            title = os.path.splitext(os.path.basename(filename))[0]
            url = apicall % ('Movie.search', title)
            result = yield self.download(url)
        for movie in result:
            self._db.add(
                'movie', moviedb=int(movie._data['id']), title=movie.title,
                imdb=movie._data.get('imdb_id', ''), data=movie._data)
        self._db.commit()
        yield result

    @kaa.coroutine()
    def match(self, metadata, id):
        if not metadata.get('hash'):
            yield False
        self._db.add('hash', moviedb=id, value=u'%s|%s' % (metadata.get('hash'), metadata.filesize))
        self._db.commit()
        yield True
