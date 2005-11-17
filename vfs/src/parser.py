# -*- coding: iso-8859-1 -*-
# -----------------------------------------------------------------------------
# parser.py - Parser for metadata
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
import stat

from kaa.notifier import Timer
import kaa.metadata

def get_mtime(item):
    if not item.filename:
        print 'no filename == no mtime :('
        return 0

    mtime = 0
    if item.isdir:
        return os.stat(item.filename)[stat.ST_MTIME]

    # mtime is the the mtime for all files having the same
    # base. E.g. the mtime of foo.jpg is the sum of the
    # mtimeof foo.jpg and foo.jpg.xml or for foo.mp3 the
    # mtime is the sum of foo.mp3 and foo.jpg.

    base = os.path.splitext(item.filename)[0]

    # TODO: add overlay support

    # TODO: Make this much faster. We should cache the listdir
    # and the stat results somewhere, maybe already split by ext
    # But since this is done in background, this is not so
    # important right now.
    files = map(lambda x: item.dirname + x, os.listdir(item.dirname))
    for f in filter(lambda x: x.startswith(base), files):
        mtime += os.stat(f)[stat.ST_MTIME]
    return mtime


def parse(db, item):
    mtime = get_mtime(item)
    if not mtime:
        print 'oops, no mtime', item
        return
    if item.data['mtime'] == mtime:
        print 'up-to-date', item
        return
    print 'scan', item
    attributes = { 'mtime': mtime }
    metadata = kaa.metadata.parse(item.filename)
    if item.data.has_key('type'):
        type = item.data['type']
    elif metadata and metadata['media'] and \
             db._object_types.has_key(metadata['media']):
        type = metadata['media']
    elif item.isdir:
        type = 'dir'
    else:
        type = 'file'

    type_list = db._object_types[type]
    for key in type_list[1].keys():
        if metadata and metadata.has_key(key) and metadata[key] != None:
            attributes[key] = metadata[key]

    # TODO: do some more stuff here:
    # - check metadata for thumbnail or cover (audio) and use kaa.thumb to store it
    # - schedule thumbnail genereation with kaa.thumb
    # - search for covers based on the file (should be done by kaa.metadata)
    # - maybe the item is now in th db so we can't add it again

    # FIXME: the items are not updated yet, the changes are still in
    # the queue and will be added to the db on commit.

    if item.dbid:
        # update
        db.update_object(item.dbid, **attributes)
        item.data.update(attributes)
    else:
        # create
        # FIXME: make sure somehow that we don't add an object that was
        # added by a different search
        db.add_object(type, name=item.basename, parent=item.parent.dbid, **attributes)
    return True


class Checker(object):
    def __init__(self, db, items, notify):
        self.db = db
        self.items = items
        self.max = len(items)
        self.pos = 0
        self.notify = notify
        Timer(self.check).start(0.01)


    def check(self):

        # TODO: maybe put the checker itself into a thread

        if not self.items:
            print 'commit changes'
            commit = self.db.commit()
            commit.connect(self.notify, 'changed')
            commit.connect(self.notify, 'up-to-date')
            return False
        self.pos += 1
        item = self.items[0]
        self.items = self.items[1:]
        if item:
            self.notify('progress', self.pos, self.max)
            parse(self.db, item)
        return True

