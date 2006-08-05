# -*- coding: iso-8859-1 -*-
# -----------------------------------------------------------------------------
# fusefs.py - Beacon Fuse Bindings
# -----------------------------------------------------------------------------
# $Id$
#
# -----------------------------------------------------------------------------
# kaa-beacon - A virtual filesystem with metadata
# Copyright (C) 2006 Dirk Meyer
#
# First Edition: Jason Tackaberry <tack@sault.org>
#                Dirk Meyer <dischi@freevo.org>
# Maintainer:    Jason Tackaberry <tack@sault.org>
#                Dirk Meyer <dischi@freevo.org>
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
import sys
import time
import logging
import stat
import fuse
import errno

import kaa.notifier
import kaa.beacon
import kaa.utils

# get logging object
log = logging.getLogger('beacon')

FuseError = fuse.FuseError

class MyStat(fuse.Stat):
    def __init__(self):
        self.st_mode = 0
        self.st_ino = 0
        self.st_dev = 0
        self.st_nlink = 0
        self.st_uid = os.getuid()
        self.st_gid = os.getgid()
        self.st_size = 0
        self.st_atime = 0
        self.st_mtime = 0
        self.st_ctime = 0


class BeaconFS(fuse.Fuse):
    def __init__(self, mountpoint, query, *args, **kw):
        self._query = query
        self._filename_map = {}
        self._query_update_time = 0
        query.signals["changed"].connect_weak(self._query_changed)
        query.monitor()

        fuse.Fuse.__init__(self, *args, **kw)

        self.multithreaded = 1
        # make it a real path because we will chdir to /
        self.mountpoint = os.path.realpath(mountpoint)
        self.parse(args=[self.mountpoint, "-f"])


    def _query_changed(self):
        """
        Notification from beacon.
        """
        self._filename_map = {}
        self._query_update_time = int(time.time())
        for item in self._query:
            if not item.isfile() and not item.isdir():
                # no file or dir, we can't link to it
                continue
            name = item.get('name')
            if name in self._filename_map:
                n = 1
                file, ext = os.path.splitext(name)
                while name in self._filename_map:
                    name = "%s-%d%s" % (file, n, ext)
                    n += 1

            self._filename_map[name] = item


    def getattr(self, path):
        """
        Return stat attributes.
        """
        st = MyStat()
        if path == '/':
            st.st_mode = stat.S_IFDIR | 0755
            st.st_nlink = 2
            st.st_atime = st.st_mtime = st.st_ctime = self._query_update_time
            return st

        file = path[1:] # assume prefixed with single /
        if file in self._filename_map:
            item = self._filename_map[file]
            st.st_mode = stat.S_IFREG | 0444 | stat.S_IFLNK
            st.st_nlink = 1
            st.st_size = len(item.filename)
            st.st_atime = st.st_mtime = st.st_ctime = item.get('mtime')
            return st
        else:
            return -errno.ENOENT


    def readdir(self, path, offset):
        """
        Return directory listing.
        """
        for r in  '.', '..':
            yield fuse.Direntry(r)
        for file in self._filename_map:
            yield fuse.Direntry(file)


    def readlink(self, path):
        """
        Return destination of the link.
        """
        file = path[1:] # assume prefixed with single /
        if file not in self._filename_map:
            return -errno.ENOENT
        return self._filename_map[file].filename


    def check(self):
        """
        Do some sanity checks to catch common gotchas with fuse.
        """

        # Python 2.4.2 and earlier has a bug that python-fuse triggers.
        # 2.4.3 known working.
        if sys.hexversion < 0x2040300:
            err = "Python versions before 2.4.3 have a bug with fuse;" + \
                  "your version is %s" % sys.version.split()[0]
            raise fuse.FuseError, err

        # Check for kernel support.
        if not os.path.exists("/dev/fuse"):
            err = "/dev/fuse not present; fuse module not loaded?"
            raise fuse.FuseError, err

        # Check that we have write access to /dev/fuse
        try:
            file("/dev/fuse", "w")
        except IOError, (err, msg):
            if err == 13:
                err = "No write access to /dev/fuse; check permissions."
                raise fuse.FuseError, err
            raise

        # Make sure fusermount is found in path.
        fusermount = kaa.utils.which("fusermount")
        if not fusermount:
            raise fuse.FuseError, "fusermount is not found in PATH."

        # If we're non-root, check that fusermount is suidroot.
        if os.geteuid() != 0:
            # This shouldn't fail, because kaa.utils.which already statted it.
            st = os.stat(fusermount)
            if st[stat.ST_UID] != 0 or not st[stat.ST_MODE] & stat.S_ISUID:
                err = "fusermount is not suid root and you're not root."
                raise fuse.FuseError, err

        if os.listdir(self.mountpoint):
            # mountpoint is not empty, fuse doesn't like that
            err = "mountpoint %s is not empty" % self.mountpoint
            raise fuse.FuseError, err


    def main(self):
        """
        Main loop for fuse. This needs to be called in a thread. On fuse
        shutdown, the kaa notifier main loop will be stopped.
        """
        self.check()
        fuse.Fuse.main(self)
        kaa.notifier.MainThreadCallback(kaa.notifier.shutdown)()
