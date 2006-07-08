# -*- coding: iso-8859-1 -*-
# -----------------------------------------------------------------------------
# mountpoint.py - Mountpoint Class for the Media Attribute
# -----------------------------------------------------------------------------
# $Id$
#
# TODO: o Mountpoint handling (rom drive mount/umount)
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

import os
import logging

from crawl import Crawler
from cdrom import Device as Cdrom

# get logging object
log = logging.getLogger('beacon')

class Mountpoint(object):
    """
    Internal class for mountpoints. More a list of attributes important
    for each mountpoint.
    """

    # TODO: make this object visible to the client and add mount and umount
    # functions to it. But we need different kinds of classes for client
    # and server because the client needs to use ipc for the mounting.

    def __init__(self, type, device, directory, beacon_dir, db, client):
        self.type = type
        self.device = device
        self.directory = directory
        self.name = None
        self.id = None
        self.beacon_dir = beacon_dir
        self.db = db
        self.overlay = ''
        self.url = ''
        self.client = client
        if not self.client:
            if type == 'hd':
                self.crawler = Crawler(db)
            if type == 'cdrom':
                self.watcher = Cdrom(self, db)
                self.watcher.signals['changed'].connect(self.load)

                
    def load(self, name):
        """
        Set name of the mountpoint (== load new media)
        """
        log.info('load %s', name)
        if name == self.name:
            return False
        self.name = name
        self.id = None
        self.url = ''
        # get the db id
        if self.name != None:
            media = self.db.query_raw(type="media", name=self.name)
            if media:
                # known, set internal id
                media = media[0]
                self.id = ('media', media['id'])
            elif not self.client:
                # no client == server == write access
                # create media entry and root filesystem
                log.info('create media entry for %s' % self.name)
                media = self.db.add_object("media", name=self.name, content='file',
                                           beacon_immediately=True)
                self.id = ('media', media['id'])
            if not self.db.query_raw(type='dir', name='', parent=self.id) and \
                   not self.client:
                log.info('create root filesystem for %s' % self.name)
                self.db.add_object("dir", name="", parent=self.id,
                                   beacon_immediately=True)
                self.db.commit(force=True)
            if media:
                self.url = media['content'] + '//' + self.directory
            if name:
                self.overlay = os.path.join(self.beacon_dir, name)
                if not os.path.isdir(self.overlay):
                    os.mkdir(self.overlay)
            else:
                self.overlay = ''
        return True


    def monitor(self, directory):
        self.crawler.append(directory)

        
    def __repr__(self):
        """
        Convert object to string (usefull for debugging)
        """
        return '<beacon.Mountpoint for %s>' % self.directory


    def __del__(self):
        return 'del', self

