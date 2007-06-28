# -*- coding: iso-8859-1 -*-
# -----------------------------------------------------------------------------
# file.py - Beacon file item
# -----------------------------------------------------------------------------
# $Id$
#
# -----------------------------------------------------------------------------
# kaa.beacon - A virtual filesystem with metadata
# Copyright (C) 2006 Dirk Meyer
#
# First Edition: Dirk Meyer <dischi@freevo.org>
# Maintainer:    Dirk Meyer <dischi@freevo.org>
#
# Please see the file AUTHORS for a complete list of authors.
#
# This library is free software; you can redistribute it and/or modify
# it under the terms of the GNU Lesser General Public License version
# 2.1 as published by the Free Software Foundation.
#
# This library is distributed in the hope that it will be useful, but
# WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
# Lesser General Public License for more details.
#
# You should have received a copy of the GNU Lesser General Public
# License along with this library; if not, write to the Free Software
# Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA
# 02110-1301 USA
#
# -----------------------------------------------------------------------------

# python imports
import os
import stat
import time
import logging

import kaa.notifier

# kaa.beacon imports
from item import Item

# get logging object
log = logging.getLogger('beacon')


class File(Item):
    """
    A file based database item.

    Attributes:
    url:         unique url of the item
    filename:    complete filename

    Functions:
    get:         get an attribute, optional argument force
    __getitem__: get an attribute
    __setitem__: set an attribute
    keys:        return all known attributes of the item
    scanned:     return True if the item is scanned
    list:        return list of subitems or directory content
    isdir:       return True if it is a directory
    isfile:      return True if it is a regular file

    Do not access attributes starting with _beacon outside kaa.beacon
    """

    def __init__(self, data, parent, overlay=False, isdir=False):
        if isinstance(data, str):
            # fake item, there is no database entry
            id = None
            filename = parent.filename + data
            data = { 'name': data }
            if parent and parent._beacon_id:
                data['parent_type'], data['parent_id'] = parent._beacon_id
            media = parent._beacon_media
            if isdir:
                filename += '/'
        elif isinstance(parent, File):
            # db data
            id = (data['type'], data['id'])
            media = parent._beacon_media
            filename = parent.filename + data['name']
            if isdir:
                filename += '/'
        elif not data['name']:
            # root directory
            id = (data['type'], data['id'])
            media = parent
            parent = None
            filename = media.mountpoint
        else:
            raise ValueError('unable to create File item from %s', data)

        Item.__init__(self, id, 'file://' + filename, data, parent, media)
        if self._beacon_data.get('scheme'):
            self.url = self._beacon_data.get('scheme') + \
                       self.url[self.url.find('://')+3:]
        
        self._beacon_overlay = overlay
        self._beacon_isdir = isdir
        self._beacon_islink = False
        self.filename = filename
        if isdir:
            ovdir = filename[len(media.mountpoint):]
            self._beacon_ovdir = media.overlay + '/' + ovdir
            self._beacon_listdir_cache = None
            if os.path.islink(filename[:-1]):
                self._beacon_islink = True


    # -------------------------------------------------------------------------
    # Public API
    # -------------------------------------------------------------------------

    def list(self, recursive=False):
        """
        Interface to kaa.beacon: List all files in the directory.
        """
        if recursive:
            return self._beacon_controller().query(parent=self, recursive=True)
        return self._beacon_controller().query(parent=self)


    # -------------------------------------------------------------------------
    # Internal API for client and server
    # -------------------------------------------------------------------------

    @kaa.notifier.yield_execution()
    def _beacon_listdir(self, cache=False, async=False):
        """
        Internal function to list all files in the directory and the overlay
        directory. The result is a list of tuples:
        basename, full filename, is_overlay, stat result
        This function gets called by the client when doing a dirname query
        and by the server for the query and inside the parser to get mtime
        information. If async is True, this function may return an
        InProgress object and not the results. In that case, connect to this
        object to get the result later.
        """
        if self._beacon_listdir_cache and cache and \
               self._beacon_listdir_cache[0] + 3 > time.time():
            # use cached result if we have and caching time is less than
            # three seconds ago
            yield self._beacon_listdir_cache[1:]

        # FIXME: This doesn't hold a reference to items, so what does?

        # FIXME: this could block for everything except media 1. So this
        # should be done in the hwmon process. But the server doesn't like
        # an InProgress return.
        try:
            # Try to list the overlay directory
            overlay_results = os.listdir(self._beacon_ovdir)
        except OSError:
            # No overlay
            overlay_results = []

        try:
            # Try to list the directory. If that fails for some reason,
            # return an empty list
            fs_results = os.listdir(self.filename)
        except OSError, e:
            log.warning(e)
            self._beacon_listdir_cache = time.time(), [], {}
            yield [], {}

        results_file_map = {}
        counter = 0
        timer = time.time()

        for is_overlay, prefix, results in \
                ((False, self.filename, fs_results),
                 (True, self._beacon_ovdir, overlay_results)):
            for r in results:
                if (is_overlay and r in results_file_map) or r[0] == ".":
                    continue
                fullpath = prefix + r
                try:
                    # append stat information to every result
                    statinfo = os.stat(fullpath)
                    if is_overlay and stat.S_ISDIR(statinfo[stat.ST_MODE]):
                        # dir in overlay, ignore
                        log.warning('skip overlay dir %s' % r[1])
                        continue
                except (OSError, IOError), e:
                    # unable to stat file, remove it from list
                    log.error(e)
                    continue

                results_file_map[r] = (r, fullpath, is_overlay, statinfo)
                counter += 1
                if async and not counter % 30 and time.time() > timer + 0.04:
                    # we are in async mode and already use too much time.
                    # call yield YieldContinue at this point to continue
                    # later.
                    timer = time.time()
                    yield kaa.notifier.YieldContinue

        # We want to avoid lambda on large data sets, so we sort the keys,
        # which is just a list of files.  This is the common case that sort()
        # is optimized for.
        keys = results_file_map.keys()
        keys.sort()
        result = [ results_file_map[x] for x in keys ]
        # store in cache
        self._beacon_listdir_cache = time.time(), result, results_file_map
        yield result, results_file_map


    def __repr__(self):
        """
        Convert object to string (usefull for debugging)
        """
        s = '<beacon.File %s' % self.filename
        if not self.url.startswith('file://'):
            s = '<beacon.File %s' % self.url
        if self._beacon_data.get('mtime') == None:
            s += ' (new)'
        else:
            s += ' (type=%s)' % str(self._beacon_data.get('type'))
        return s + '>'


    # -------------------------------------------------------------------------
    # Internal API for client
    # -------------------------------------------------------------------------

    def _beacon_request(self, callback=None, *args, **kwargs):
        """
        Request the item to be scanned.
        """
        f = self._beacon_controller()._beacon_request
        f(self.filename, self._beacon_database_update, callback,
          *args, **kwargs)
        return None


    # -------------------------------------------------------------------------
    # Internal API for server
    # -------------------------------------------------------------------------

    def _beacon_mtime(self):
        """
        Return modification time of the item itself.

        mtime is the the mtime for all files having the same base. E.g. the
        mtime of foo.jpg is the sum of the mtime of foo.jpg and foo.jpg.xml
        or for foo.mp3 the mtime is the sum of foo.mp3 and foo.jpg.
        """
        if self._beacon_isdir:
            # Directory handling. Maybe add directory cover images
            # to the mtime list. But in most cases it is not needed. A
            # new file for the cover would also effect the directory
            # mtime itself.
            try:
                mtime = os.stat(self.filename)[stat.ST_MTIME]
            except (OSError, IOError):
                return None
            try:
                return max(os.stat(self._beacon_ovdir)[stat.ST_MTIME], mtime)
            except (OSError, IOError):
                return mtime

        # Normal file
        fullname = self._beacon_data['name']
        basename, ext = fullname, ''
        pos = basename.rfind('.')
        if pos > 0:
            ext = basename[pos:]
            basename = basename[:pos]

        # FIXME: move this logic to kaa.metadata. The best way would be to
        # use the info modules for that kind of information, but we may not
        # know the type here. This code here is only for testing.
        # FIXME: this also only supports ext in lower case
        if ext in ('.avi',):
            # subtitles for avi + cover
            special_exts = ( '.srt', '.png', '.jpg' )
        elif ext in ('.gif', '.png', '.jpg', '.jpeg'):
            # bins xml files
            special_exts = ( '.xml', )
        else:
            # cover
            special_exts = ( '.png', '.jpg' )

        listdir_file_map = self._beacon_parent._beacon_listdir(cache=True)[1]
        # calculate the new modification time
        try:
            mtime = listdir_file_map[fullname][3][stat.ST_MTIME]
        except KeyError:
            return 0
        for ext in special_exts:
            fname = listdir_file_map.get(basename+ext)
            if fname:
                mtime += fname[3][stat.ST_MTIME]
            fname = listdir_file_map.get(fullname+ext)
            if fname:
                mtime += fname[3][stat.ST_MTIME]
        return mtime
