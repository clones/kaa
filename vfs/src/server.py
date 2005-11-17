# -*- coding: iso-8859-1 -*-
# -----------------------------------------------------------------------------
# server.py - Server interface for the VFS
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

from kaa.base import ipc, weakref
from kaa.base.db import *
from kaa.notifier import OneShotTimer

from db import Database
from monitor import Monitor

class Server(object):
    def __init__(self, dbdir):
        self._db = Database(dbdir)

        self.register_object_type_attrs("video",
            title = (unicode, ATTR_KEYWORDS),
            width = (int, ATTR_SIMPLE),
            height = (int, ATTR_SIMPLE),
            length = (int, ATTR_SIMPLE))

        self.register_object_type_attrs("audio",
            title = (unicode, ATTR_KEYWORDS),
            artist = (unicode, ATTR_KEYWORDS | ATTR_INDEXED),
            album = (unicode, ATTR_KEYWORDS),
            genre = (unicode, ATTR_INDEXED),
            samplerate = (int, ATTR_SIMPLE),
            length = (int, ATTR_SIMPLE),
            bitrate = (int, ATTR_SIMPLE),
            trackno = (int, ATTR_SIMPLE))

        self.register_object_type_attrs("image",
            width = (int, ATTR_SEARCHABLE),
            height = (int, ATTR_SEARCHABLE),
            date = (unicode, ATTR_SEARCHABLE))

        # TODO: add more known types

        self._db.commit()
        self._db.wait()


    def register_object_type_attrs(self, *args, **kwargs):
        return self._db.register_object_type_attrs(*args, **kwargs)


    def monitor(self, callback, **query):
        monitor = Monitor(callback, self._db, query)
        print 'create %s' % monitor
        OneShotTimer(monitor.update).start(0)
        return monitor, monitor.id



_vfs_db = {}

def connect(dbdir):
    dbdir = os.path.normpath(os.path.abspath(dbdir))
    print 'connect to', dbdir

    # TODO: delete databases not used anymore

    if not dbdir in _vfs_db:
        server = Server(dbdir)
        # FIXME: use weakref
        _vfs_db[dbdir] = server
    return _vfs_db[dbdir]

_ipc = ipc.IPCServer('vfs')
_ipc.register_object(connect, 'vfs')
