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
    def __init__(self, data, parent, db):
        self.db = db
        self.parent = None

        # self.dirname always ends with a slash
        # if the item is a dir, self.filename also ends with a slash
        # self.url does not end with a slash (except root)

        # If parent is not set, this is a root node.
        # A root node is always part of the db already
        if not parent:
            self.data = data
            self.url = 'file:/' + self.data['name']
            self.dirname = self.data['name']
            self.filename = self.data['name']
            self.isdir = True
            self.basename = '/'
            self.dbid = self.data['type'], self.data["id"]
            return

        if isinstance(data, dict):
            self.data = data
            self.basename = self.data['name']
            self.dbid = self.data['type'], self.data["id"]
        else:
            self.basename = data
            self.dbid = None
            self.data = { 'name': data, 'mtime': UNKNOWN }

        # check if the item is based on a file
        if not isinstance(parent, str):
            self.parent = parent
            parent = parent.filename
        if parent:
            self.url = 'file://' + parent + self.basename
            self.dirname = parent
            self.filename = parent + self.basename
            if os.path.isdir(self.filename):
                self.filename += '/'
                self.isdir = True
            else:
                self.isdir = False

        # TODO: handle files/parents not based on file:

        # TODO: give item an os.* like iterface, e.g. add
        # open for files and listdir for dirs

        # TODO: make it possible to change an item in the client


    def __str__(self):
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
