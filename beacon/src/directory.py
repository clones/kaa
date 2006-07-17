# -*- coding: iso-8859-1 -*-
# -----------------------------------------------------------------------------
# directory.py - Beacon directory item
# -----------------------------------------------------------------------------
# $Id$
#
# -----------------------------------------------------------------------------
# kaa-beacon - A virtual filesystem with metadata
# Copyright (C) 2006 Dirk Meyer
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
import os
import stat
import time
import logging

import kaa.notifier

# kaa.beacon imports
from item import Item

# get logging object
log = logging.getLogger('beacon')

UNKNOWN = -1

class Directory(Item):
    """
    A directory based database item.

    Attributes:
    url:         unique url of the item
    filename:    complete dirname, ends with '/'

    Functions:
    get:         get an attribute, optional argument force
    __getitem__: get an attribute
    __setitem__: set an attribute
    keys:        return all known attributes of the item
    scanned:     return True if the item is scanned
    list:        return list of subitems
    isdir:       return True
    isfile:      return False

    Do not access attributes starting with _beacon outside kaa.beacon
    """

    def __init__(self, data, parent):
        # Notes: filename end with '/'
        if isinstance(data, str):
            # fake item, there is no database entry
            id = None
            self.filename = parent.filename + data + '/'
            data = { 'name': data, 'mtime': UNKNOWN }
            if parent and parent._beacon_id:
                data['parent_type'], data['parent_id'] = parent._beacon_id
            media = parent._beacon_media
        elif isinstance(parent, Directory):
            # db data
            id = (data['type'], data['id'])
            media = parent._beacon_media
            self.filename = parent.filename + data['name'] + '/'
        else:
            # root directory
            id = (data['type'], data['id'])
            media = parent
            parent = None
            self.filename = media.mountpoint

        self._beacon_islink = False
        if os.path.islink(self.filename[:-1]):
            self._beacon_islink = True

        Item.__init__(self, id, 'file://' + self.filename, data, parent, media)
        self._beacon_overlay = False
        self._beacon_isdir = True
        self._beacon_ovdir = media.overlay + '/' + \
                             self.filename[len(media.mountpoint):]
        self._beacon_listdir_cache = None


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
        Convert object to string
        """
        str = '<beacon.Directory %s' % self.filename
        if self._beacon_data['mtime'] == UNKNOWN:
            str += ' (new)'
        return str + '>'


    # -------------------------------------------------------------------------
    # Internal API for client
    # -------------------------------------------------------------------------

    def _beacon_request(self, callback=None, *args, **kwargs):
        """
        Request the item to be scanned.
        """
        f = self._beacon_controller()._beacon_request
        f(self.filename[:-1], self._beacon_database_update, callback,
          *args, **kwargs)
        return None


    # -------------------------------------------------------------------------
    # Internal API for server
    # -------------------------------------------------------------------------

    def _beacon_mtime(self):
        """
        Return modification time of the item itself.

        The modification time of a directory is the max value of the mtime from
        the directory itself and the overlay directory (if that exists).
        """
        if os.path.isdir(self._beacon_ovdir):
            try:
                return max(os.stat(self._beacon_ovdir)[stat.ST_MTIME],
                           os.stat(self.filename)[stat.ST_MTIME])
            except (OSError, IOError):
                pass
        try:
            return os.stat(self.filename)[stat.ST_MTIME]
        except (OSError, IOError):
            return None
