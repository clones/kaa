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

# kaa imports
import kaa
import kaa.db
from kaa.saxutils import ElementParser

from core import Database

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


class Entry(object):

    def items(self):
        """
        Return items in the TVDB dict
        """
        if not self.data:
            return {}
        return self.data['data'].items()

    def __getattr__(self, attr):
        """
        Get season metadata from db
        """
        if attr in self.data.keys():
            return self.data[attr]
        data = self.data.get('data') or {}
        if attr in data:
            return data[attr]


class Episode(Entry):
    """
    Object for an episode
    """
    def __init__(self, tvdb, series, season, episode):
        self.tvdb = tvdb
        self.series = series
        self.season = season
        self.episode = episode
        records = self.tvdb._db.query(type='episode', parent=('series', series.id),
            season=self.season.season, episode=self.episode)
        self.data = {}
        if records:
            self.data = records[0]

    @property
    def image(self):
        """
        Episode image
        """
        if self.filename:
            return self.tvdb.hostname + '/banners/' + self.filename


class Season(Entry):
    """
    Object for a season
    """
    def __init__(self, tvdb, series, season):
        self.tvdb = tvdb
        self.series = series
        self.season = season
        self.data = {}

    def get_episode(self, episode):
        """
        Get Episode object
        """
        return Episode(self.tvdb, self.series, self, episode)

    @property
    def banner(self):
        banner = []
        for entry in self.series._get_banner(u'season'):
            if entry.get('Season') == str(self.season):
                banner.append(entry)
        return banner


class Series(Entry):
    """
    Object for a series
    """
    def __init__(self, tvdb, data):
        self.tvdb = tvdb
        self.data = data

    def add_alias(self, alias):
        """
        Add an alias name for the series
        """
        self.tvdb._updatedb('alias', alias, parent=('series', self.data['id']))
        self.tvdb._db.commit()
        self.tvdb.force_resync()

    def get_season(self, season):
        """
        Get Season object
        """
        return Season(self.tvdb, self, season)

    @property
    def banner2(self):
        return self.tvdb._db.query(type='banner', parent=('series', self.data['id']))

    def _get_banner(self, btype):
        banner = []
        for r in self.tvdb._db.query(type='banner', parent=('series', self.data['id']), btype=btype):
            entry = r.get('data')
            for key, value in entry.items():
                if key.lower().endswith('path'):
                    entry[key] = self.tvdb.hostname + '/banners/' + str(value)
            entry.pop('BannerType')
            entry.pop('id')
            banner.append(entry)
        return banner

    @property
    def fanart(self):
        banner = []
        for entry in self._get_banner(u'fanart'):
            entry['resolution'] = entry.pop('BannerType2')
            banner.append(entry)
        return banner

    @property
    def poster(self):
        banner = []
        for entry in self._get_banner(u'poster'):
            entry['resolution'] = entry.pop('BannerType2')
            banner.append(entry)
        return banner

    @property
    def banner(self):
        banner = []
        for entry in self._get_banner(u'series'):
            banner.append(entry)
        return banner


class TVDB(Database):
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

    @property
    def aliases(self):
        """
        Aliases known to the DB
        """
        return [ a['tvdb'] for a in self._db.query(type='alias') ]

    def _updatedb(self, type, tvdb, parent=None, **kwargs):
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

    @kaa.coroutine()
    def _process(self, url, parent=None):
        """
        Process XML URL and update DB. The changes are commited but
        the version is not changed
        """
        for name, data in (yield parse(url))[1]:
            if name == 'Episode':
                if not parent:
                    raise RuntimeError()
                self._updatedb(
                    'episode', int(data.get('id')), name=data.get('EpisodeName'), parent=parent,
                    season=int(data.get('SeasonNumber')), episode=int(data.get('EpisodeNumber')),
                    data=data)
            elif name == 'Series':
                data['timestamp'] = time.time()
                parent = ('series', self._updatedb(
                        'series', int(data.get('id')), name=data.get('SeriesName'), data=data))
            elif name == 'Banner':
                self._updatedb(
                    'banner', int(data.get('id')), btype=data.get('BannerType'), data=data, parent=parent)
            else:
                log.error('unknown element: %s', name)
        self._db.commit()
        yield parent

    def _get_series_by_name(self, name):
         """
         Get a Series object based on the alias name
         """
         data = self._db.query(type='alias', tvdb=name)
         if not data:
             return None
         return Series(self, self._db.query(type='series', id=data[0]['parent_id'])[0])

    @kaa.coroutine()
    def _get_series_by_id(self, id):
        """
        Get a Series object based on the series ID
        """
        data = self._db.query(type='series', tvdb=id)
        if data:
            yield Series(self, data[0])
        if not self._db.query(type='metadata'):
            attr, data = (yield parse(self.hostname + '/api/Updates.php?type=none'))
            data = dict(data)
            self._db.add('metadata', servertime=int(data['Time']), localtime=int(time.time()))
        parent = (yield self._process(self.api + 'series/%s/all/en.xml' % id))
        yield self._process(self.api + 'series/%s/banners.xml' % id, parent=parent)
        data = self._db.query(type='series', tvdb=id)
        self.force_resync()
        if data:
            yield Series(self, data[0])

    @kaa.coroutine()
    def search(self, name):
        """
        Search for a series
        """
        result = []
        url = self.hostname + '/api/GetSeries.php?seriesname=%s' % urllib.quote(name)
        for name, data in (yield parse(url))[1]:
            result.append(('thetvdb:' + data['seriesid'], data['SeriesName'],
                           data.get('FirstAired', None), data.get('Overview', None), data))
        yield result

    @kaa.coroutine()
    def match(self, alias, id):
        """
        Match this filename to the given server id
        """
        if not alias:
            yield False
        series = (yield self._get_series_by_id(id))
        if not series:
            yield False
        series.add_alias(alias)
        series.add_alias(series.data['name'])
        self._db.commit()
        yield True

    @kaa.coroutine()
    def sync(self):
        """
        Sync database with server
        """
        if not self._db.query(type='metadata'):
            yield
        metadata = self._db.query(type='metadata')[0]
        diff = int(time.time() - metadata['localtime'])
        if diff < 24 * 60 * 60:
            update = 'updates_day.xml'
        elif diff < 7 * 24 * 60 * 60:
            update = 'updates_week.xml'
        elif diff < 28 * 7 * 24 * 60 * 60:
            update = 'updates_month.xml'
        else:
            update = ''
        series = [ record['tvdb'] for record in self._db.query(type='series') ]
        url = self.api + 'updates/%s' % update
        attr, updates = (yield parse(url))
        banners = []
        for element, data in updates:
            if element == 'Series':
                if int(data['id']) in series and int(data['time']) > metadata['servertime']:
                    url = self.api + 'series/%s/en.xml' % data['id']
                    yield self._process(url)
            if element == 'Episode':
                if int(data['Series']) in series and int(data['time']) > metadata['servertime']:
                    url = self.api + 'episodes/%s/en.xml' % data['id']
                    parent = 'series', self._db.query(type='series', tvdb=int(data['Series']))[0]['id']
                    yield self._process(url, parent=parent)
            if element == 'Banner':
                if int(data['Series']) in series: # and int(data['time']) > metadata['servertime']:
                    if not int(data['Series']) in banners:
                        banners.append(int(data['Series']))
        # banner update
        for series in banners:
            parent = 'series', self._db.query(type='series', tvdb=series)[0]['id']
            yield self._process(self.api + 'series/%s/banners.xml' % series, parent=parent)
        self._db.update(metadata, servertime=int(attr['time']), localtime=int(time.time()))
        self.force_resync()
