# -*- coding: iso-8859-1 -*-
# -----------------------------------------------------------------------------
# item.py - Item of the VFS
# -----------------------------------------------------------------------------
# $Id: device.py 799 2005-09-16 14:27:36Z rshortt $
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

UNKNOWN = -1

class Item(object):
    def __init__(self, dbid, url, data, parent, db):
        self.dbid = dbid
        self.url = url
        self.data = data
        self.parent = parent
        self.db = db

        # TODO: remove this from Item, it only matters for
        # Directory and File
        self.dirname = ''
        self.basename = ''
        self.filename = ''

        # TODO: remove this
        self.isdir = False

        # TODO: make it possible to change an item in the client


    def __str__(self):
        """
        Convert object to string (usefull for debugging)
        """
        str = '<vfs.Item %s' % self.data['name']
        if self.data['mtime'] == UNKNOWN:
            str += '(new)'
        return str + '>'


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
    def __init__(self, dbid, dirname, basename, filename, url, data, parent, db):
        Item.__init__(self, dbid, url, data, parent, db)
        self.dirname = dirname
        self.basename = basename
        self.filename = filename
        self.isdir = True


    def listdir(self):
        """
        List the directory. This returns a database object.
        """
        return self.db.query(dirname=self.filename)


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
    def __init__(self, dbid, dirname, basename, filename, url, data, parent, db):
        Item.__init__(self, dbid, url, data, parent, db)
        self.dirname = dirname
        self.basename = basename
        self.filename = filename


    def __str__(self):
        """
        Convert object to string (usefull for debugging)
        """
        str = '<vfs.File %s' % self.filename
        if self.data['mtime'] == UNKNOWN:
            str += '(new)'
        return str + '>'


def create(data, parent, db):
    """
    Create an Item object or an inherted class if possible.
    """
    if isinstance(data, dict):
        basename = data['name']
        dbid = data['type'], data['id']
    else:
        basename = data
        dbid = None
        data = { 'name': data, 'mtime': UNKNOWN }

    # check parent and if parent indicates a directory
    dirname = ''
    if parent:
        if isinstance(parent, str):
            if parent != '/':
                dirname = parent
                parent = None
        else:
            dirname = parent.filename

    # Note: dirname always ends with a slash
    # if the item is a dir, self.filename also ends with a slash
    # self.url does not end with a slash (except root)

    if dirname:
        # we have a dirname, that indicates the item is either
        # a Directory or a File
        filename = dirname + basename
        url = 'file://' + filename
        if os.path.isdir(filename):
            # it is a directory
            return Directory(dbid, dirname, basename, filename + '/',
                             url, data, parent, db)
        # it is a file
        return File(dbid, dirname, basename, filename, url, data, parent, db)

    if parent == '/':
        return Directory(dbid, '/', '/', '/', 'file:///', data, parent, db)
        
    # TODO: handle files/parents not based on file

    # TODO: we guess it is a root dir now

    # it is something else
    return Item()
