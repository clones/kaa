# -*- coding: iso-8859-1 -*-
# -----------------------------------------------------------------------------
# tvdb.py - TVDB Database
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
from kaa.inotify import INotify
from kaa.saxutils import ElementParser

# get logging object
log = logging.getLogger('beacon.tvdb')

@kaa.threaded()
def parse(url):
    """
    Threaded XML parser
    """
    results = []
    def handle(element):
        info = {}
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
        records = self.tvdb._db.query(type='episode', parent=('series', series.id), season=self.season.season, episode=self.episode)
        self.data = {}
        if records:
            self.data = records[0]

    @property
    def image(self):
        """
        Episode image
        """
        if self.filename:
            return 'http://www.thetvdb.com/banners/' + self.filename


class Season(Entry):
    """
    Object for a season
    """
    def __init__(self, tvdb, series, season):
        self.tvdb = tvdb
        self.series = series
        self.season = season

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
        self.tvdb.version += 1
        open(self.tvdb._versionfile, 'w').write(str(self.tvdb.version))

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
                    entry[key] = 'http://www.thetvdb.com/banners/' + str(value)
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


# This regular expression matches most tv shows. It requires the
# format to be either like s01e02 or 1x02. There are files out there
# in file sharing tools that will not work, e.g. a small search showed
# files like series.102.title. It is hard to detect that this in fact
# is a series and the 102 not part of a movie name.
VIDEO_SHOW_REGEXP = 's?([0-9]|[0-9][0-9])[xe]([0-9]|[0-9][0-9])[ \-\._]'

# Next regexp for bad files as described above. If the show is in the
# database already, it is ok if the file starts with a known name
# followed by a three or four digest number.
VIDEO_SHOW_REGEXP2 = '[ \-\._]([0-9]?[0-9])([0-9][0-9])[ \-\._]'

class Filename(object):
    """
    Object for a video filename
    """
    # indicator if we are sure that is a tv series or not
    sure = True

    def __init__(self, tvdb, filename):
        self.filename = filename
        filename = os.path.basename(filename).lower()
        self.tvdb = tvdb
        match = re.split(VIDEO_SHOW_REGEXP, filename)
        if len(match) != 4:
            # try the other regexp
            match = re.split(VIDEO_SHOW_REGEXP2, filename)
            if len(match) != 4:
                # it is no tv series
                self.alias = self._season = self._episode = None
                return
            # we are not sure
            self.sure = False
        self.alias = kaa.str_to_unicode(' '.join(re.split('[.\-_ :]', match[0]))).strip()
        self._season = int(match[1])
        self._episode = int(match[2])

    @property
    def series(self):
        """
        Series object
        """
        if not self.alias:
            return None
        return self.tvdb.get_series_by_alias(kaa.str_to_unicode(self.alias))

    @property
    def season(self):
        """
        Season object
        """
        if not self._season:
            return None
        series = self.series
        if not series:
            return None
        return series.get_season(self._season)

    @property
    def episode(self):
        """
        Episode object
        """
        if not self._episode:
            return None
        season = self.season
        if not season:
            return None
        return season.get_episode(self._episode)

    def search(self):
        """
        Search server what this filename may be
        """
        if not self.alias:
            return []
        return self.tvdb.search_series(self.alias)

    def match(self, id):
        """
        Match this filename to the given server id
        """
        return self.tvdb.match_series(self.alias, id)


class TVDB(kaa.Object):
    """
    Database object for thetvdb.org
    """
    __kaasignals__ = {
        'changed':
            '''
            Signal when the database on disc changes
            ''',
        }

    def __init__(self, database, apikey='1E9534A23E6D7DC0'):
        super(TVDB, self).__init__()
        self._apikey = apikey
        # set up the database and the version file
        if not os.path.exists(os.path.dirname(database)):
            os.makedirs(os.path.dirname(database))
        self._db = kaa.db.Database(database)
        self._versionfile = database + '.version'
        if not os.path.exists(self._versionfile):
            open(self._versionfile, 'w').write('0')
        try:
            self.version = int(open(self._versionfile).read())
        except ValueError:
            self.version = 0
        INotify().watch(self._versionfile, INotify.CLOSE_WRITE).connect(self._db_updated)
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

    def _db_updated(self, *args):
        """
        Callback from INotify when the version file changed
        """
        try:
            version = int(open(self._versionfile).read())
        except ValueError:
            version = self.version + 1
        if version != self.version:
            self.version = version
            self.signals['changed'].emit()

    @property
    def aliases(self):
        """
        Aliases known to the DB
        """
        return [ a['tvdb'] for a in self._db.query(type='alias') ]

    def get_metadata(self, key):
        """
        Get database metadata
        """
        if not self._db.query(type='metadata'):
            return None
        metadata = self._db.query(type='metadata')[0]['metadata']
        if not metadata:
            return None
        return metadata.get(key)

    def set_metadata(self, key, value):
        """
        Set database metadata
        """
        if not self._db.query(type='metadata'):
            return None
        entry = self._db.query(type='metadata')[0]
        metadata = entry['metadata'] or {}
        metadata[key] = value
        self._db.update_object(entry, metadata=metadata)
        self._db.commit()

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
            return self._db.add_object(type, tvdb=tvdb, **kwargs)['id']
        self._db.update_object(current[0], **kwargs)
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
                self._updatedb('episode', int(data.get('id')), name=data.get('EpisodeName'), parent=parent,
                               season=int(data.get('SeasonNumber')), episode=int(data.get('EpisodeNumber')), data=data)
            elif name == 'Series':
                data['timestamp'] = time.time()
                parent = ('series', self._updatedb('series', int(data.get('id')), name=data.get('SeriesName'), data=data))
            elif name == 'Banner':
                self._updatedb('banner', int(data.get('id')), btype=data.get('BannerType'), data=data, parent=parent)
            else:
                log.error('unknown element: %s', name)
        self._db.commit()
        yield parent

    def get_series_by_alias(self, alias):
        """
        Get a Series object based on the alias name
        """
        data = self._db.query(type='alias', tvdb=alias)
        if not data:
            return None
        return Series(self, self._db.query(type='series', id=data[0]['parent_id'])[0])

    @kaa.coroutine()
    def get_series_by_id(self, id):
        """
        Get a Series object based on the series ID
        """
        data = self._db.query(type='series', tvdb=id)
        if data:
            yield Series(self, data[0])
        if not self._db.query(type='metadata'):
            print 'sync metadata'
            attr, data = (yield parse('http://www.thetvdb.com/api/%s/updates/' % self._apikey))
            self._db.add_object('metadata', servertime=int(attr['time']), localtime=int(time.time()))
        print 'sync data'
        parent = (yield self._process('http://www.thetvdb.com/api/%s/series/%s/all/en.xml' % (self._apikey, id)))
        yield self._process('http://www.thetvdb.com/api/%s/series/%s/banners.xml' % (self._apikey, id), parent=parent)
        data = self._db.query(type='series', tvdb=id)
        self.version += 1
        open(self._versionfile, 'w').write(str(self.version))
        if data:
            yield Series(self, data[0])

    def from_filename(self, filename):
        """
        Return a fully parsed Filename object
        """
        return Filename(self, filename)

    @kaa.coroutine()
    def search_series(self, name):
        """
        Search for a series
        """
        url = 'http://www.thetvdb.com/api/GetSeries.php?seriesname=%s' % urllib.quote(name)
        yield [ data for name, data in (yield parse(url))[1] ]

    @kaa.coroutine()
    def match_series(self, alias, id):
        """
        Match this filename to the given server id
        """
        if not alias:
            yield False
        series = (yield self.get_series_by_id(id))
        if not series:
            yield False
        series.add_alias(alias)
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
            uodate = 'updates_week.xml'
        elif diff < 28 * 7 * 24 * 60 * 60:
            update = 'updates_month.xml'
        else:
            update = ''
        series = [ record['tvdb'] for record in self._db.query(type='series') ]
        url = 'http://www.thetvdb.com/api/%s/updates/%s' % (self._apikey, update)
        print url
        attr, updates = (yield parse(url))
        banners = []
        for element, data in updates:
            if element == 'Series':
                if int(data['id']) in series and int(data['time']) > metadata['servertime']:
                    url = 'http://www.thetvdb.com/api/%s/series/%s/en.xml' % (self._apikey, data['id'])
                    print url
                    yield self._process(url)
            if element == 'Episode':
                if int(data['Series']) in series and int(data['time']) > metadata['servertime']:
                    url = 'http://www.thetvdb.com/api/%s/episodes/%s/en.xml' % (self._apikey, data['id'])
                    print url
                    parent = 'series', self._db.query(type='series', tvdb=int(data['Series']))[0]['id']
                    yield self._process(url, parent=parent)
            if element == 'Banner':
                if int(data['Series']) in series: # and int(data['time']) > metadata['servertime']:
                    if not int(data['Series']) in banners:
                        banners.append(int(data['Series']))
        # banner update
        for series in banners:
            parent = 'series', self._db.query(type='series', tvdb=series)[0]['id']
            yield self._process('http://www.thetvdb.com/api/%s/series/%s/banners.xml' % (self._apikey, series), parent=parent)
        self._db.update_object(metadata, servertime=int(attr['time']), localtime=int(time.time()))
        self.version += 1
        open(self._versionfile, 'w').write(str(self.version))
