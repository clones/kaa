# -*- coding: iso-8859-1 -*-
# -----------------------------------------------------------------------------
# file.py - File item of the VFS
# -----------------------------------------------------------------------------
# $Id: item.py 1273 2006-03-11 19:34:08Z dmeyer $
#
# TODO: handle all the FIXME and TODO comments inside this file and
#       add docs for functions, variables and how to use this file
#
# -----------------------------------------------------------------------------
# kaa-vfs - A virtual filesystem with metadata
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

# kaa.vfs imports
from item import Item

UNKNOWN = -1

class File(Item):
    """
    A file based item.
    Object Attributes:
    url, filename, getattr, setattr, keys

    Do not access attributes starting with _vfs outside kaa.vfs
    """
    def __init__(self, data, parent, overlay=False):
        if isinstance(data, str):
            # fake item, there is no database entry
            id = None
            self.filename = parent.filename + data
            data = { 'name': data, 'mtime': UNKNOWN }
            if parent and parent._vfs_id:
                data['parent_type'], data['parent_id'] = parent._vfs_id
            media = parent._vfs_media
        elif isinstance(parent, Directory):
            # db data
            id = (data['type'], data['id'])
            media = parent._vfs_media
            self.filename = parent.filename + data['name']

        Item.__init__(self, id, 'file://' + self.filename, data, parent, media)
        self._vfs_overlay = overlay


    def _vfs_mtime(self):
        # mtime is the the mtime for all files having the same
        # base. E.g. the mtime of foo.jpg is the sum of the
        # mtimeof foo.jpg and foo.jpg.xml or for foo.mp3 the
        # mtime is the sum of foo.mp3 and foo.jpg.
        search = self._vfs_data['name']
        if search.rfind('.') > 0:
            search = search[:search.rfind('.')]
        mtime = 0
        for basename, filename in self._vfs_parent._vfs_os_listdir():
            if basename.startswith(search):
                mtime += os.stat(filename)[stat.ST_MTIME]
        return mtime


    def __repr__(self):
        """
        Convert object to string (usefull for debugging)
        """
        str = '<vfs.File %s' % self.filename
        if self._vfs_data['mtime'] == UNKNOWN:
            str += ' (new)'
        return str + '>'


# make it possible to override these

