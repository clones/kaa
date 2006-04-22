# -*- coding: iso-8859-1 -*-
# -----------------------------------------------------------------------------
# directory.py - Beacon directory item
# -----------------------------------------------------------------------------
# $Id$
#
# -----------------------------------------------------------------------------
# kaa-beacon - A virtual filesystem with metadata
# Copyright (C) 2005 Dirk Meyer
#
# First Edition: Dirk Meyer <dmeyer@tzi.de>
# Maintainer:    Dirk Meyer <dmeyer@tzi.de>
#
# Please see the file doc/CREDITS for a complete list of authors.
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

# kaa.beacon imports
from item import Item

# get logging object
log = logging.getLogger('beacon')

UNKNOWN = -1

class Directory(Item):
    """
    A directory based database item.

    Attributes:
    url:      unique url of the item
    filename: filename of the directory on hd
    listdir:  list all items in that directory
    getattr:  function to get an attribute
    setattr:  function to set an attribute
    keys:     function to return all known attributes of the item

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
            self.filename = media.directory

        self._beacon_islink = False
        if os.path.islink(self.filename[:-1]):
            self._beacon_islink = True

        Item.__init__(self, id, 'file://' + self.filename, data, parent, media)
        self._beacon_overlay = False
        self._beacon_isdir = True
        self._beacon_ovdir = media.overlay + '/' + self.filename[len(media.directory):]
        self._beacon_listdir_cache = None

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
            return 0


    def _beacon_request(self):
        """
        Request the item to be scanned.
        """
        self._beacon_database_update(self._beacon_db()._beacon_request(self.filename[:-1]))


    def _beacon_listdir(self, cache=False):
        """
        Internal function to list all files in the directory and the overlay
        directory. The result is a list of tuples:
        basename, full filename, is_overlay, stat result
        """
        if self._beacon_listdir_cache and cache and \
               self._beacon_listdir_cache[0] + 3 > time.time():
            # use cached result if we have and caching time is less than
            # three seconds ago
            return self._beacon_listdir_cache[1]

        try:
            # Try to list the directory. If that fails for some reason,
            # return an empty list
            listdir = os.listdir(self.filename)
            result = [ [ x, self.filename + x, False ] for x in listdir
                       if not x.startswith('.') ]
        except OSError, e:
            log.warning(e)
            self._beacon_listdir_cache = time.time(), []
            return []

        try:
            # Try to list the overlay directory
            result += [ [ x, self._beacon_ovdir + x, True ] \
                          for x in os.listdir(self._beacon_ovdir) \
                          if not x.startswith('.') and not x in listdir ]
        except OSError:
            # No overlay
            pass
        
        for r in result[:]:
            try:
                # append stat information to every result
                r.append(os.stat(r[1]))
                if r[2] and stat.S_ISDIR(r[3][stat.ST_MODE]):
                    # overlay dir, remove
                    log.warning('skip overlay dir %s' % r[1])
                    result.remove(r)
            except (OSError, IOError), e:
                # unable to stat file, remove it from list
                log.error(e)
                result.remove(r)
        # sort results
        result.sort(lambda x,y: cmp(x[0], y[0]))
        # store in cache
        self._beacon_listdir_cache = time.time(), result
        # return results
        return result[:]


    def __repr__(self):
        """
        Convert object to string (usefull for debugging)
        """
        str = '<beacon.Directory %s' % self.filename
        if self._beacon_data['mtime'] == UNKNOWN:
            str += ' (new)'
        return str + '>'


    def listdir(self):
        """
        Interface to kaa.beacon: List all files in the directory.
        """
        if not self._beacon_id:
            log.info('requesting data for %s', self)
            self._beacon_request()
        return self._beacon_db().query(parent=self)

