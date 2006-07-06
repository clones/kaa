# -*- coding: iso-8859-1 -*-
# -----------------------------------------------------------------------------
# file.py - Beacon file item
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
import logging

# kaa.beacon imports
from item import Item
from directory import Directory

# get logging object
log = logging.getLogger('beacon')


UNKNOWN = -1

class File(Item):
    """
    A file based database item.

    Attributes:
    url:      unique url of the item
    filename: filename of the item on hd
    getattr:  function to get an attribute
    setattr:  function to set an attribute
    keys:     function to return all known attributes of the item
    scanned:  returns True if the item is scanned

    Do not access attributes starting with _beacon outside kaa.beacon
    """
    def __init__(self, data, parent, overlay=False):
        if isinstance(data, str):
            # fake item, there is no database entry
            id = None
            self.filename = parent.filename + data
            data = { 'name': data, 'mtime': UNKNOWN }
            if parent and parent._beacon_id:
                data['parent_type'], data['parent_id'] = parent._beacon_id
            media = parent._beacon_media
        elif isinstance(parent, Directory):
            # db data
            id = (data['type'], data['id'])
            media = parent._beacon_media
            self.filename = parent.filename + data['name']

        Item.__init__(self, id, 'file://' + self.filename, data, parent, media)
        self._beacon_overlay = overlay


    # -------------------------------------------------------------------------
    # Internal API for client and server
    # -------------------------------------------------------------------------

    def __repr__(self):
        """
        Convert object to string (usefull for debugging)
        """
        str = '<beacon.File %s' % self.filename
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
        f = self._beacon_db()._beacon_request
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
        mtime = listdir_file_map[fullname][3][stat.ST_MTIME]
        for ext in special_exts:
            if basename+ext in listdir_file_map:
                mtime += listdir_file_map[basename+ext][3][stat.ST_MTIME]
            if fullname+ext in listdir_file_map:
                mtime += listdir_file_map[fullname+ext][3][stat.ST_MTIME]
        return mtime
