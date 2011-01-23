# -*- coding: iso-8859-1 -*-
# -----------------------------------------------------------------------------
# tvdb.py - TVDB Database
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

__all__ = [ 'TVDB' ]

# python imports
import os
import sys
import xml.sax
import urllib
import re
import time
import logging
import zipfile

# kaa imports
import kaa
import kaa.db
from kaa.saxutils import ElementParser

import core

# get logging object
log = logging.getLogger('beacon.tvdb')

WORKER_THREAD = 'WEBMETADATA'

@kaa.threaded(WORKER_THREAD)
def parse(url):
    """
    Threaded XML parser
    """
    results = []
    def handle(element):
        info = {}
        if element.content:
            results.append((element.tagname, element.content))
        else:
            for child in element:
                if child.content:
                    info[child.tagname] = child.content
            results.append((element.tagname, info))
    e = ElementParser()
    e.handle = handle
    parser = xml.sax.make_parser()
    parser.setContentHandler(e)
    parser.parse(url)
    return e.attr, results

@kaa.threaded(WORKER_THREAD)
def download(url):
    return urllib.urlopen(url).read()

class Episode(core.Episode):
    """
    Object for an episode
    """
    def __init__(self, tvdb, series, season, episode):
        super(Episode, self).__init__()
        self.tvdb = tvdb
        self.series = series
        self.season = season
        self.episode = episode
        self.number = episode
        records = self.tvdb._db.query(type='episode', parent=('series', series.id),
            season=self.season.season, episode=self.episode)
        self.data = {}
        if records:
            self.data = records[0]
            self.title = self.data.get('name')
            self.overview = self.data['data'].get('Overview')
            if self.data['data'].get('filename'):
                self.image = self.tvdb.hostname + '/banners/' + self.data['data'].get('filename')


class Season(core.Season):
    """
    Object for a season
    """
    def __init__(self, tvdb, series, season):
        super(Season, self).__init__()
        self.tvdb = tvdb
        self.series = series
        self.season = season
        self.data = {}
        self.number = season

    def get_episode(self, episode):
        """
        Get Episode object
        """
        return Episode(self.tvdb, self.series, self, episode)

    # @property
    # def banner(self):
    #     banner = []
    #     for entry in self.series._get_banner(u'season'):
    #         if entry.get('Season') == str(self.season):
    #             banner.append(entry)
    #     return banner


class Series(core.Series):
    """
    Object for a series
    """
    def __init__(self, tvdb, data):
        super(Series, self).__init__()
        self._keys = self._keys + [ 'banner', 'posters', 'images' ]
        self.title = data['name']
        self.id = data['id']
        self.tvdb = tvdb
        self.data = data
        if data.get('data'):
            self.overview = data['data'].get('Overview')

    def get_season(self, season):
        """
        Get Season object
        """
        return Season(self.tvdb, self, season)

    def _get_banner(self, btype):
        banner = []
        for r in self.tvdb._db.query(type='banner', parent=('series', self.data['id']), btype=btype):
            entry = r.get('data')
            for key, value in entry.items():
                if key.lower().endswith('path'):
                    entry[key] = self.tvdb.hostname + '/banners/' + str(value)
            entry.pop('BannerType')
            entry.pop('id')
            i = core.Image()
            i.url = entry['BannerPath']
            i.thumbnail = entry.get('ThumbnailPath', i.url)
            i.data = entry
            banner.append(i)
        banner.sort(lambda x,y: -cmp(float(x.data.get('Rating', 0)), float(y.data.get('Rating', 0))))
        return banner

    @property
    def images(self):
        return self._get_banner(u'fanart')

    @property
    def posters(self):
        return self._get_banner(u'poster')

    @property
    def banner(self):
        return self._get_banner(u'series')

class SearchResult(core.Series):
    def __init__(self, id, title, overview, year):
        self.id = id
        self.title = title
        self.overview = overview
        self.year = None
        if year and len(year.split('-')) == 3:
            self.year = year.split('-')[0]

class TVDB(core.Database):
    """
    Database object for thetvdb.org
    """

    scheme = 'thetvdb:'

    def __init__(self, database, apikey='1E9534A23E6D7DC0'):
        super(TVDB, self).__init__(database)
        self.hostname = 'http://www.thetvdb.com'
        self._apikey = apikey
        self.api = '%s/api/%s/' % (self.hostname, self._apikey)
        # set up the database itself
        self._db.register_object_type_attrs("metadata",
            servertime = (int, kaa.db.ATTR_SEARCHABLE),
            localtime = (int, kaa.db.ATTR_SEARCHABLE),
            metadata = (dict, kaa.db.ATTR_SIMPLE),
        )
        self._db.register_object_type_attrs("series",
            tvdb = (int, kaa.db.ATTR_SEARCHABLE),
            name = (unicode, kaa.db.ATTR_SEARCHABLE),
            data = (dict, kaa.db.ATTR_SIMPLE),
        )
        self._db.register_object_type_attrs("alias",
            tvdb = (unicode, kaa.db.ATTR_SEARCHABLE),
        )
        self._db.register_object_type_attrs("episode",
            tvdb = (int, kaa.db.ATTR_SEARCHABLE),
            name = (unicode, kaa.db.ATTR_SEARCHABLE),
            season = (int, kaa.db.ATTR_SEARCHABLE),
            episode = (int, kaa.db.ATTR_SEARCHABLE),
            data = (dict, kaa.db.ATTR_SIMPLE),
        )
        self._db.register_object_type_attrs("banner",
            tvdb = (int, kaa.db.ATTR_SEARCHABLE),
            btype = (unicode, kaa.db.ATTR_SEARCHABLE),
            data = (dict, kaa.db.ATTR_SIMPLE),
        )

    def _update_db(self, type, tvdb, parent=None, **kwargs):
        """
        Update the database, does not commit changes
        """
        if parent:
            current = self._db.query(type=type, tvdb=tvdb, parent=parent)
        else:
            current = self._db.query(type=type, tvdb=tvdb)
        if not current:
            if parent:
                kwargs['parent'] = parent
            return self._db.add(type, tvdb=tvdb, **kwargs)['id']
        self._db.update(current[0], **kwargs)
        return current[0]['id']

    @kaa.coroutine(policy=kaa.POLICY_SYNCHRONIZED)
    def _update_series(self, id):
        tmp = kaa.tempfile('thetvdb/%s' % id)
        if not os.path.isdir(tmp):
            os.mkdir(tmp)
            return
        f = open('%s/en.zip' % tmp, 'w')
        f.write((yield download(self.api + 'series/%s/all/en.zip' % id)))
        f.close()
        z = zipfile.ZipFile('%s/en.zip' % tmp)
        z.extract('en.xml', tmp)
        z.extract('banners.xml', tmp)
        os.unlink(tmp + '/en.zip')
        parent = None
        for name, data in (yield parse(open(tmp + '/en.xml')))[1]:
            if name == 'Series':
                s = self._update_db('series', int(data.get('id')), name=data.get('SeriesName'), data=data)
                parent = ('series', s)
            elif name == 'Episode':
                if not parent:
                    raise RuntimeError()
                self._update_db('episode', int(data.get('id')), name=data.get('EpisodeName'), parent=parent,
                    season=int(data.get('SeasonNumber')), episode=int(data.get('EpisodeNumber')),
                    data=data)
            else:
                log.error('unknown element: %s', name)
        self._db.commit()
        os.unlink(tmp + '/en.xml')
        for name, data in (yield parse(open(tmp + '/banners.xml')))[1]:
            if name == 'Banner':
                self._update_db('banner', int(data.get('id')), btype=data.get('BannerType'),
                    data=data, parent=parent)
            else:
                log.error('unknown element: %s', name)
        self._db.commit()
        os.unlink(tmp + '/banners.xml')
        os.rmdir(tmp)

    def parse(self, filename, metadata):
        """
        Get a Series object based on the alias name
        """
        if not 'series' in metadata:
            return None
        data = self._db.query(type='alias', tvdb=metadata.get('series'))
        if not data:
            return None
        return Series(self, self._db.query(type='series', id=data[0]['parent_id'])[0])

    @kaa.coroutine()
    def search(self, name):
        """
        Search for a series
        """
        result = []
        url = self.hostname + '/api/GetSeries.php?seriesname=%s' % urllib.quote(name)
        for name, data in (yield parse(url))[1]:
            result.append(SearchResult('thetvdb:' + data['seriesid'], data['SeriesName'],
                           data.get('Overview', None), data.get('FirstAired', None)))
        yield result

    @kaa.coroutine()
    def match(self, metadata, id):
        """
        Match the metadata to the given id. Metadata can either be a
        string with the name to match or a kaa.metadata object.
        """
        if isinstance(metadata, (str, unicode)):
            alias = kaa.str_to_unicode(metadata)
        else:
            alias = metadata.get('series')
        if not alias:
            log.error('no alias given')
            yield False
        if not self._db.query(type='metadata'):
            attr, data = (yield parse(self.hostname + '/api/Updates.php?type=none'))
            data = dict(data)
            self._db.add('metadata', servertime=int(data['Time']), localtime=int(time.time()))
        data = self._db.query(type='series', tvdb=id)
        if not data:
            log.info('query thetvdb for %s' % id)
            for i in range(3):
                # try to get results three times before giving up
                yield self._update_series(id)
                data = self._db.query(type='series', tvdb=id)
                if data:
                    break
            self.force_resync()
        if not data:
            log.error('no result from server')
            yield False
        self._update_db('alias', alias, parent=('series', data[0]['id']))
        self._update_db('alias', data[0]['name'], parent=('series', data[0]['id']))
        self._db.commit()
        series = Series(self, data[0])
        self.force_resync()
        yield True

    @kaa.coroutine(policy=kaa.POLICY_SYNCHRONIZED)
    def sync(self):
        """
        Sync database with server
        """
        if not self._db.query(type='metadata'):
            yield
        metadata = self._db.query(type='metadata')[0]
        series = [ record['tvdb'] for record in self._db.query(type='series') ]
        url = self.hostname + '/api/Updates.php?type=all&time=%s' % metadata['servertime']
        attr, updates = (yield parse(url))
        banners = []
        for element, data in updates:
            if element == 'Series':
                if int(data) in series:
                    yield self._update_series(data)
            if element == 'Time':
                self._db.update(metadata, servertime=int(data), localtime=int(time.time()))
        self.force_resync()
