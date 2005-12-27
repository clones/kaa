# -*- coding: iso-8859-1 -*-
# -----------------------------------------------------------------------------
# item.py - Item of the VFS
# -----------------------------------------------------------------------------
# $Id$
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

import os

import util

UNKNOWN = -1

class Item(object):
    def __init__(self, dbid, url, data, parent, media):
        self.dbid = dbid
        self.url = url
        self.data = data
        self.parent = parent
        self.db = None
        self.media = media


    def __str__(self):
        """
        Convert object to string (usefull for debugging)
        """
        return '<vfs.Item %s>' % self.url


    def set_data(self, data):
        """
        Callback for add_object.
        """
        # TODO: do we need to set more attributes?
        self.data = data
        self.dbid = data['type'], data['id']


    def __getitem__(self, key):
        if self.data.has_key(key):
            return self.data[key]
        if self.data.has_key('tmp:' + key):
            return self.data['tmp:' + key]

        # TODO: maybe get cover from parent (e.g. cover in a dir)
        # Or should that be stored in each item

        return None


class Directory(Item):
    """
    A directory based item.
    """
    def __init__(self, dbid, basename, filename, url, data, parent,
                 overlay, media):
        Item.__init__(self, dbid, url, data, parent, media)
        self.basename = basename
        self.filename = filename
        self.isdir = True
        self.overlay = overlay
        self._os_listdir = None


    def listdir(self):
        """
        List the directory. This returns a database object.
        """
        if self.db:
            return self.db.query(dirname=self.filename)
        raise AttributeError('item has no db object')


    def os_listdir(self):
        """
        Return (cached) os.listdir information including the overlay dir.
        The result is a list of basename, url.
        """
        if self._os_listdir == None:
            listing = util.listdir(self.filename[:-1], self.media)
            self._os_listdir = [ (x[x.rfind('/')+1:], x) for x in listing ]
        return self._os_listdir

        
    def __str__(self):
        """
        Convert object to string (usefull for debugging)
        """
        str = '<vfs.Directory %s' % self.filename
        if self.data['mtime'] == UNKNOWN:
            str += '(new)'
        return str + '>'
    

class File(Item):
    """
    A file based item.
    """
    def __init__(self, dbid, basename, filename, url, data, parent,
                 overlay, media):
        Item.__init__(self, dbid, url, data, parent, media)
        self.basename = basename
        self.filename = filename
        self.overlay = overlay
        self.isdir = False


    def __str__(self):
        """
        Convert object to string (usefull for debugging)
        """
        str = '<vfs.File %s' % self.filename
        if self.data['mtime'] == UNKNOWN:
            str += '(new)'
        return str + '>'


# TODO: add media class or mountpoint

def create(data, parent, media):
    """
    Create an Item object or an inherted class if possible.
    """

    # FIXME: handle items not based on files here

    if isinstance(data, dict):
        if parent == None:
            # root fileystem for the media, always valid and in the db
            dirname = media.directory
            return Directory((data['type'], data['id']), '', dirname,
                             'file:/%s/' % dirname, data, parent, False, media)
        # Data is based on a db entry. This means we also have
        # a parent as db entry
        dbid = data['type'], data['id']
        type = data['type']

        if type.startswith('track'):
            # data is a track of a dvd/vcd/audiocd an a media or in a file
            return Item(dbid, parent.url + '/' + data['name'], data, parent, media)
        basename = data['name']
        overlay = data['overlay']
        filename = parent.filename + basename
        if overlay:
            filename = media.overlay + filename
        url = 'file://' + filename
    else:
        # Looks like data is string (url). This means no db entry, maybe the parent
        # is also not set (client db read only). The media is always valid.
        url = data
        filename = data[7:]
        basename = os.path.basename(filename)
        dbid = None
        data = { 'name': data, 'mtime': UNKNOWN }
        type = ''
        overlay = filename.startswith(media.overlay)

    if type == 'dir' or (not type and os.path.isdir(filename)):
        # it is a directory
        return Directory(dbid, basename, filename + '/',
                         url, data, parent, overlay, media)
    # it is a file
    return File(dbid, basename, filename, url, data, parent, overlay, media)
