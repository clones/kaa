import os
import sys
import xml.sax
import urllib
import re
import time

import kaa
import kaa.db
from kaa.saxutils import ElementParser

@kaa.threaded()
def parse(url):
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

class Episode(object):
    def __init__(self, tvdb, series, season, episode):
        self.tvdb = tvdb
        self.series = series
        self.season = season
        self.episode = episode
        records = self.tvdb._db.query(type='episode', parent=('series', series.id), season=self.season.season, episode=self.episode)
        self.data = None
        if records:
            self.data = records[0]

    def items(self):
        if not self.data:
            return {}
        return self.data['data'].items()
    
class Season(object):
    def __init__(self, tvdb, series, season):
        self.tvdb = tvdb
        self.series = series
        self.season = season

    def get_episode(self, episode):
        return Episode(self.tvdb, self.series, self, episode)


class Series(object):
    def __init__(self, tvdb, data):
        self.tvdb = tvdb
        self.data = data

    def add_alias(self, alias):
        self.tvdb._updatedb('alias', alias, parent=('series', self.data['id']))

    def get_season(self, season):
        return Season(self.tvdb, self, season)

    def __getattr__(self, attr):
        if attr in self.data.keys():
            return self.data[attr]

# we need a better regexp
VIDEO_SHOW_REGEXP = "s?([0-9]|[0-9][0-9])[xe]([0-9]|[0-9][0-9])[^0-9]"
VIDEO_SHOW_REGEXP_SPLIT = re.compile("[\.\- ]" + VIDEO_SHOW_REGEXP + "[\.\- ]*").split

class Filename(object):
    def __init__(self, tvdb, filename):
        self.filename = filename
        filename = os.path.basename(filename).lower()
        self.tvdb = tvdb
        if not re.search(VIDEO_SHOW_REGEXP, filename):
            self.alias = self._season = self._episode = None
            return
        self.alias = kaa.str_to_unicode(' '.join(re.split('[.-_ :]', VIDEO_SHOW_REGEXP_SPLIT(filename)[0])))
        self._season, self._episode = [ int(x) for x in re.search(VIDEO_SHOW_REGEXP, filename).groups() ]

    @property
    def series(self):
        if not self.alias:
            return None
        return self.tvdb.get_series_by_alias(kaa.str_to_unicode(self.alias))

    @property
    def season(self):
        if not self._season:
            return None
        return self.series.get_season(self._season)

    @property
    def episode(self):
        if not self._episode:
            return None
        return self.season.get_episode(self._episode)

    def search(self):
        if not self.alias:
            return []
        return self.tvdb.search_series(self.alias)

    @kaa.coroutine()
    def match(self, id):
        if not self.alias:
            yield False
        series = (yield self.tvdb.get_series_by_id(id))
        if not series:
            yield False
        series.add_alias(self.alias)
        yield True


class TVDB(object):
    def __init__(self, database, apikey='1E9534A23E6D7DC0'):
        self._apikey = apikey
        self._db = kaa.db.Database(database)
        self._db.register_object_type_attrs("metadata",
            servertime = (int, kaa.db.ATTR_SEARCHABLE),
            localtime = (int, kaa.db.ATTR_SEARCHABLE),
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

    def _updatedb(self, type, tvdb, parent=None, **kwargs):
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
        for name, data in (yield parse(url))[1]:
            if name == 'Episode':
                if not parent:
                    raise RuntimeError()
                self._updatedb('episode', int(data.get('id')), name=data.get('EpisodeName'), parent=parent,
                               season=int(data.get('SeasonNumber')), episode=int(data.get('EpisodeNumber')), data=data)
            elif name == 'Series':
                parent = ('series', self._updatedb('series', int(data.get('id')), name=data.get('SeriesName'), data=data))
            elif name == 'Banner':
                pass
            else:
                print name, data

    def get_series_by_alias(self, alias):
        data = self._db.query(type='alias', tvdb=alias)
        if not data:
            return None
        return Series(self, self._db.query(type='series', id=data[0]['parent_id'])[0])

    @kaa.coroutine()
    def get_series_by_id(self, id):
        data = self._db.query(type='series', tvdb=id)
        if data:
            yield Series(self, data[0])
        if not self._db.query(type='metadata'):
            print 'sync metadata'
            attr, data = (yield parse('http://www.thetvdb.com/api/%s/updates/' % self._apikey))
            self._db.add_object('metadata', servertime=int(attr['time']), localtime=int(time.time()))
        print 'sync data'
        yield self._process('http://www.thetvdb.com/api/%s/series/%s/all/en.xml' % (self._apikey, id))
        # FIXME: fetch banner
        data = self._db.query(type='series', tvdb=id)
        if data:
            yield Series(self, data[0])

    def from_filename(self, filename):
        return Filename(self, filename)

    @kaa.coroutine()
    def search_series(self, name):
        url = 'http://www.thetvdb.com/api/GetSeries.php?seriesname=%s' % urllib.quote(name)
        yield [ data for name, data in (yield parse(url))[1] ]

    @kaa.coroutine()
    def sync(self):
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
            # FIXME: banner update
        self._db.update_object(metadata, servertime=int(attr['time']), localtime=int(time.time()))
