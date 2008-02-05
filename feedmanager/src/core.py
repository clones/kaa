# -*- coding: iso-8859-1 -*-
# -----------------------------------------------------------------------------
# core.py - Feedmanager Core providing Feed and Entry
# -----------------------------------------------------------------------------
# $Id$
#
# -----------------------------------------------------------------------------
# kaa.feedmanager - Manage RSS/Atom Feeds
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
import sys
import os
import md5
import urllib
import urllib2
import logging
from xml.dom import minidom

# kaa imports
import kaa
import kaa.net.url
import kaa.beacon
from kaa.strutils import str_to_unicode, unicode_to_str

# get manager module
import manager

# get logging object
log = logging.getLogger('feedmanager')

# ##################################################################
# some generic entry/feed stuff
# ##################################################################

class Entry(dict):

    def __getattr__(self, attr):
        if attr == 'basename' and not 'basename' in self.keys():
            basename = os.path.basename(self['url'])
            if self.url.endswith('/'):
                ext = os.path.splitext(self['url'])[1]
                basename = self['title'].replace('/', '') + ext
            self['basename'] = unicode_to_str(basename)
        return self.get(attr)

    def fetch(self, filename):
        log.info('%s -> %s' % (self.url, filename))
        tmpname = os.path.join(os.path.dirname(filename),
                               '.' + os.path.basename(filename))
        return kaa.net.url.fetch(self.url, filename, tmpname)


class Feed(object):

    NEXT_ID = 0
    IMAGEDIR = None

    def __init__(self, url, destdir):
        self.url = url
        self.dirname = destdir
        self._manager = manager
        self._entries = []
        self._download = True
        self._num = 0
        self._keep = True
        self._updating = False
        if not os.path.isdir(destdir):
            os.makedirs(destdir)
        self.id = Feed.NEXT_ID
        Feed.NEXT_ID += 1


    def configure(self, download=True, num=0, keep=True):
        """
        Configure feed
        num:      number of items from the feed (0 == all, default)
        keep:     keep old entries not in feed anymore (download only)
        verbose:  print status on stdout
        """
        self._download = download
        self._num = num
        self._keep = keep
        manager.save()


    def get_config(self):
        """
        Get feed configuration.
        """
        return dict(id = self.id,
                    url = self.url,
                    directory = self.dirname,
                    download = self._download,
                    num = self._num,
                    keep = self._keep)

    def _readxml(self, node):
        """
        Read XML node with feed configuration and cache.
        """
        for d in node.childNodes:
            if not d.nodeName == 'directory':
                continue
            self._download = d.getAttribute('download').lower() == 'true'
            self._num = int(d.getAttribute('num'))
            self._keep = d.getAttribute('keep').lower() == 'true'
            for node in d.childNodes:
                if not node.nodeName == 'entry':
                    continue
                fname = unicode_to_str(node.getAttribute('filename')) or None
                self._entries.append((node.getAttribute('url'), fname))
        

    def _writexml(self, node):
        """
        Write XML node with feed configuration and cache.
        """
        node.setAttribute('url', self.url)
        doc = node.ownerDocument
        d = doc.createElement('directory')
        for attr in ('download', 'keep'):
            if getattr(self, '_' + attr):
                d.setAttribute(attr, 'true')
            else:
                d.setAttribute(attr, 'false')
            d.setAttribute('num', str(self._num))
        d.appendChild(doc.createTextNode(self.dirname))
        node.appendChild(d)
        for url, fname in self._entries:
            e = doc.createElement('entry')
            e.setAttribute('url', url)
            if fname:
                e.setAttribute('filename', str_to_unicode(fname))
            d.appendChild(e)


    @kaa.yield_execution()
    def _get_image(self, url):
        """
        Download image and store it to the image dir. Returns image
        filename.
        """
        url = unicode_to_str(url)
        fname = md5.md5(url).hexdigest() + os.path.splitext(url)[1]
        fname = os.path.join(self.IMAGEDIR, fname)
        if os.path.isfile(fname):
            yield fname
        yield kaa.net.url.fetch(url, fname)
        yield fname


    @kaa.yield_execution()
    def update(self, verbose=False):
        """
        Update feed.
        """
        def print_status(s):
            sys.stdout.write("%s\r" % s.get_progressbar())
            sys.stdout.flush()

        if self._updating:
            log.error('feed %s is already updating', self.url)
            yield False
        self._updating = True
        log.info('update feed %s', self.url)

        # get directory information
        query = kaa.beacon.query(filename=self.dirname)
        if not query.valid:
            yield query.wait()
        beacondir = query.get()
        
        listing = beacondir.list()
        if not listing.valid:
            yield listing.wait()
            
        allurls = [ f.url for f in listing ]

        num = self._num
        allfiles = [ e[1] for e in self._entries ]
        entries = self._entries
        new_entries = []

        for entry in self:
            if isinstance(entry, kaa.InProgress):
                # dummy entry to signal waiting
                yield entry
                continue

            log.info('process %s', entry.url)
            filename = None

            if not self._download and entry.url in allurls:
                # already in beacon list
                pass
            elif not self._download:
                # use url as name
                entry['name'] = unicode_to_str(entry.url)
                i = kaa.beacon.add_item(parent=beacondir, **entry)
            else:
                # download
                filename = os.path.join(self.dirname, entry.basename)
                if not os.path.isfile(filename) and filename in allfiles:
                    # file not found, check if it was downloaded before. If
                    # so, the user deleted it and we do not fetch it again
                    pass
                elif os.path.isfile(filename):
                    # File already downloaded.
                    # FIXME: make sure the file is up-to-date
                    pass
                else:
                    async = entry.fetch(filename)
                    if verbose:
                        async.get_status().connect(print_status, async.get_status())
                    yield async
                    if not os.path.isfile(filename):
                        log.error('error fetching', entry.url)
                        continue

                if os.path.isfile(filename):
                    item = yield kaa.beacon.get(filename)
                    if not item.scanned():
                        yield item.scan()
                    if 'date' in entry:
                        item['timestamp'] = entry['date']
                    for key in ('title', 'description'):
                        if key in entry:
                            item[key] = entry[key]

            new_entries.append((entry['url'], filename))
            num -= 1
            if num == 0:
                break

        log.info('*** finished with %s ***', self.url)
        manager.save()

        # delete old files or remove old entries from beacon
        for url, filename in entries:
            if (self._keep and self._download) or (url, filename) in new_entries:
                continue
            if not filename:
                # delete old entries from beacon
                for f in beacondir.list():
                    if f.url == url:
                        f.delete()
            elif os.path.isfile(filename):
                # delete file on disc
                os.unlink(filename)
        self._updating = False
        self._entries = new_entries
        yield True
    

    @kaa.yield_execution()
    def remove(self):
        """
        Remove entries from this feed.
        """
        log.info('remove %s', self.url)
        if self._keep or self._download:
            # only delete links in the filesystem
            return

        # get directory information
        query = kaa.beacon.query(filename=self.dirname)
        if not query.valid:
            yield query.wait()
        beacondir = query.get()
        allurls = [ e[0] for e in self._entries ]
        listing = beacondir.list()
        if isinstance(listing, kaa.InProgress):
            # FIXME: can this happen? Shouldn't list always return a Query
            # object and that may or may not be finished?
            listing = yield listing
        for entry in listing:
            if entry.url in allurls:
                log.info('delete %s', entry.url)
                entry.delete()
