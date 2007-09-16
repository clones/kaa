# -*- coding: iso-8859-1 -*-
# -----------------------------------------------------------------------------
# rss.py - RSS Feed implementation
# -----------------------------------------------------------------------------
# $Id$
#
# -----------------------------------------------------------------------------
# kaa.beacon.server - A virtual filesystem with metadata
# Copyright (C) 2007 Dirk Meyer
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

# python imports
import time
import logging
import urllib2

# kaa imports
import kaa.notifier

# feedmanager imports
import feedparser as _feedparser
import core

# get logging object
log = logging.getLogger('beacon.feed')
isotime = '%a, %d %b %Y %H:%M:%S'

@kaa.notifier.execute_in_thread()
def feedparser(url):
    """
    feedparser.parse wrapper in a thread.
    """
    return _feedparser.parse(urllib2.urlopen(url))


class Feed(core.Feed):
    """
    RSS Feed.
    """

    def __iter__(self):
        """
        Iterate over feed entries.
        """
        feed = feedparser(self.url)
        yield feed
        feed = feed.get_result()

        if not feed.entries:
            log.error('no entries in %s' % self.url)
            raise StopIteration

        # basic information
        feedimage = None
        if feed.feed.get('image'):
            feedimage = feed.feed.get('image').get('href')

        if feedimage:
            # FIXME: beacon does not thumbnail the image without
            # a rescan of the directory!
            feedimage = self._get_image(feedimage)
            if isinstance(feedimage, kaa.notifier.InProgress):
                yield feedimage
                feedimage = feedimage.get_result()

        # real iterate
        for f in feed.entries:

            metadata = {}

            if feedimage:
                metadata['image'] = feedimage
            if 'updated' in f.keys():
                timestamp = f.updated
                if timestamp.find('+') > 0:
                    timestamp = timestamp[:timestamp.find('+')].strip()
                if timestamp.rfind(' ') > timestamp.rfind(':'):
                    timestamp = timestamp[:timestamp.rfind(' ')]
                try:
                    t = time.strptime(timestamp, isotime)
                    metadata['timestamp'] = int(time.mktime(t))
                except ValueError:
                    log.error('bad "updated" string: %s', timestamp)

            if 'itunes_duration' in f.keys():
                duration = 0
                for p in f.itunes_duration.split(':'):
                    duration = duration * 60 + int(p)
                metadata['length'] = duration
            if 'summary' in f.keys():
                metadata['description']=f.summary
            if 'title' in f.keys():
                metadata['title'] = f.title

            if 'enclosures' in f.keys():
                # FIXME: more details than expected
                if len(f.enclosures) > 1:
                    log.warning('more than one enclosure in %s' % self.url)
                metadata['url'] = f.enclosures[0].href
                for ptype in ('video', 'audio', 'image'):
                    if f.enclosures[0].type.startswith(ptype):
                        metadata['type'] = ptype
                        break
            elif 'link' in f.keys():
                # bad RSS style
                metadata['url'] = f.link
            else:
                log.error('no link in entry for %s' % self.url)
                continue

            # FIXME: add much better logic here, including
            # getting a good basename for urls ending with /
            # based on type.
            # create entry
            entry = core.Entry(**metadata)
            yield entry
