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


# Python imports
import os
import stat
import logging

# kaa imports
from kaa.notifier import Timer
import kaa.metadata

# get logging object
log = logging.getLogger('vfs')

def get_mtime(item):
    if not item.filename:
        log.info('no filename == no mtime :(')
        return 0
    if not item.parent:
        log.info('no parent == no mtime :(')
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
    if not hasattr(item.parent, '_os_listdir'):
        # FIXME: This is a bad hack, just testing!
        item.parent._os_listdir = os.listdir(item.parent.filename)
    files = map(lambda x: item.dirname + x, item.parent._os_listdir)
    for f in filter(lambda x: x.startswith(base), files):
        mtime += os.stat(f)[stat.ST_MTIME]
    return mtime


def parse(db, item):
    mtime = get_mtime(item)
    if not mtime:
        log.info('oops, no mtime %s' % item)
        return
    if not item.parent:
        log.error('no parent %s' % item)
        return
    if item.data['mtime'] == mtime:
        log.debug('up-to-date %s' % item)
        return
    log.info('scan %s' % item)
    attributes = { 'mtime': mtime }
    metadata = kaa.metadata.parse(item.filename)
    if item.data.has_key('type'):
        type = item.data['type']
    elif metadata and metadata['media'] and \
             db.object_types.has_key(metadata['media']):
        type = metadata['media']
    elif item.isdir:
        type = 'dir'
    else:
        type = 'file'

    type_list = db.object_types[type]
    for key in type_list[1].keys():
        if metadata and metadata.has_key(key) and metadata[key] != None:
            attributes[key] = metadata[key]

    # TODO: do some more stuff here:
    # - check metadata for thumbnail or cover (audio) and use kaa.thumb to store it
    # - schedule thumbnail genereation with kaa.thumb
    # - search for covers based on the file (should be done by kaa.metadata)
    # - maybe the item is now in th db so we can't add it again

    # Note: the items are not updated yet, the changes are still in
    # the queue and will be added to the db on commit.

    if item.dbid:
        # Update
        db.update_object(item.dbid, **attributes)
        item.data.update(attributes)
    else:
        # Create. Maybe the obejct is already in the db. This could happen because
        # of bad timing but should not matter. Only one entry will be there after
        # the next update
        db.add_object(type, name=item.basename, parent=item.parent.dbid, **attributes)
    return True


class Checker(object):
    def __init__(self, monitor, db, items):
        self.monitor = monitor
        self.db = db
        self.items = items
        self.max = len(items)
        self.pos = 0
        Timer(self.check).start(0.01)


    def check(self):

        # TODO: maybe put the checker itself into a thread. But if we do this,
        # make sure we handle self.monitor correctly because this is a weakref

        if not self.items:
            self.db.commit()
            if self.monitor:
                self.monitor.callback('checked')
                self.monitor.update(False)
            return False
        self.pos += 1
        item = self.items[0]
        self.items = self.items[1:]
        if item:
            self.notify('progress', self.pos, self.max, item.url)
            parse(self.db, item)
        return True


    def notify(self, *args, **kwargs):
        if self.monitor:
            self.monitor.callback(*args, **kwargs)
