# -*- coding: iso-8859-1 -*-
# -----------------------------------------------------------------------------
# server.py - Server interface for Beacon
# -----------------------------------------------------------------------------
# $Id$
#
# -----------------------------------------------------------------------------
# kaa.beacon.server - A virtual filesystem with metadata
# Copyright (C) 2006-2009 Dirk Meyer
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


# Python imports
import os
import sys
import logging

# kaa imports
import kaa.rpc

# kaa.beacon server imports
import parser
from controller import Controller
from db import *
from monitor import Monitor
from crawl import Crawler
from config import config
import plugins

# get logging object
log = logging.getLogger('beacon.server')


class Server(object):
    """
    Server for the virtual filesystem to handle write access to the db and
    scanning / monitoring of queries.
    """
    def __init__(self, dbdir, scheduler=None):
        log.info('start beacon')
        try:
            self.ipc = kaa.rpc.Server('beacon')
        except IOError, e:
            kaa.beacon.thumbnail.thumbnail.disconnect()
            log.error('beacon: %s' % e)
            time.sleep(0.1)
            sys.exit(0)

        self.ipc.signals['client-connected'].connect(self.client_connect)
        self.ipc.register(self)

        self._dbdir = dbdir
        self._db = Database(dbdir)
        self._next_client = 0

        self._db.register_inverted_index('keywords', min = 2, max = 30)

        self._db.register_object_type_attrs("dir",
            image_from_items = (bool, ATTR_SIMPLE),
            title = (unicode, ATTR_SIMPLE),
            artist = (unicode, ATTR_SIMPLE),
            album = (unicode, ATTR_SIMPLE),
            length = (float, ATTR_SIMPLE))

        # files

        self.register_file_type_attrs("video",
            title = (unicode, ATTR_SEARCHABLE | ATTR_IGNORE_CASE | ATTR_INVERTED_INDEX, 'keywords'),
            width = (int, ATTR_SIMPLE),
            height = (int, ATTR_SIMPLE),
            length = (float, ATTR_SIMPLE),
            scheme = (str, ATTR_SIMPLE),
            description = (unicode, ATTR_SIMPLE),
            timestamp = (int, ATTR_SEARCHABLE))

        self.register_file_type_attrs("audio",
            title = (unicode, ATTR_SEARCHABLE | ATTR_IGNORE_CASE | ATTR_INVERTED_INDEX, 'keywords'),
            artist = (unicode, ATTR_SEARCHABLE | ATTR_INDEXED | ATTR_IGNORE_CASE | ATTR_INVERTED_INDEX, 'keywords'),
            album = (unicode, ATTR_SEARCHABLE | ATTR_IGNORE_CASE | ATTR_INVERTED_INDEX, 'keywords'),
            genre = (unicode, ATTR_SEARCHABLE | ATTR_INDEXED | ATTR_IGNORE_CASE),
            samplerate = (int, ATTR_SIMPLE),
            length = (float, ATTR_SIMPLE),
            bitrate = (int, ATTR_SIMPLE),
            trackno = (int, ATTR_SIMPLE),
            userdate = (unicode, ATTR_SIMPLE),
            description = (unicode, ATTR_SIMPLE),
            timestamp = (int, ATTR_SEARCHABLE))

        self.register_file_type_attrs("image",
            width = (int, ATTR_SEARCHABLE),
            height = (int, ATTR_SEARCHABLE),
            comment = (unicode, ATTR_SEARCHABLE | ATTR_IGNORE_CASE | ATTR_INVERTED_INDEX, 'keywords'),
            rotation = (int, ATTR_SIMPLE),
            author = (unicode, ATTR_SIMPLE),
            timestamp = (int, ATTR_SEARCHABLE))

        # tracks for rom discs or iso files

        self.register_track_type_attrs("dvd",
            length = (float, ATTR_SIMPLE),
            audio = (list, ATTR_SIMPLE),
            chapters = (int, ATTR_SIMPLE),
            subtitles = (list, ATTR_SIMPLE))

        self.register_track_type_attrs("vcd",
            audio = (list, ATTR_SIMPLE))

        self.register_track_type_attrs("cdda",
            title = (unicode, ATTR_SEARCHABLE | ATTR_INVERTED_INDEX, 'keywords'),
            artist = (unicode, ATTR_SEARCHABLE | ATTR_INDEXED | ATTR_INVERTED_INDEX, 'keywords'))

        # list of current clients
        self.clients = []

        config.load(os.path.join(dbdir, "config"), sync=True)
        config.watch()
        log.warning("USING SCHEDULER: %s", scheduler)
        if scheduler:
            config.autosave = False
            config.scheduler.policy = scheduler

        # commit and wait for the results (there are no results,
        # this code is only used to force waiting until the db is
        # set up.
        self._db.commit()

        # give database to controller / hardware monitor
        rootfs = {
            'beacon.id': 'kaa.beacon.root',
            'block.device': '',
            'volume.mount_point': '/'
        }

        self.item_controller = Controller(self, self._db, rootfs)
        self._db.commit()

        # load plugins
        plugins.load(self, self._db)

        for dir in config.monitors:
            self.monitor_directory(os.path.expandvars(os.path.expanduser(dir)))

    # -------------------------------------------------------------
    # client handling
    # -------------------------------------------------------------

    def client_connect(self, client):
        """
        Connect a new client to the server.
        """
        client.signals['closed'].connect_once(self.client_disconnect, client)
        self._next_client += 1
        self.clients.append((self._next_client, client, []))
        media = []
        for m in self._db.medialist:
            media.append((m.id, m.prop))
        client.rpc('connect', self._next_client, self._dbdir, media)

    def client_disconnect(self, client):
        """
        IPC callback when a client is lost.
        """
        for client_info in self.clients[:]:
            if client == client_info[1]:
                log.info('disconnect client')
                for m in client_info[2]:
                    m.stop()
                self.clients.remove(client_info)
        self._db.read_lock.unlock(client_info[1], True)

    # -------------------------------------------------------------
    # hardware monitor callbacks
    # -------------------------------------------------------------

    def media_changed(self, media):
        """
        Media mountpoint changed or added.
        """
        for id, client, monitors in self.clients:
            client.rpc('device.changed', media.id, media.prop)
        if not media.crawler:
            if not media.get('block.device'):
                log.info('start crawler for /')
                media.crawler = Crawler(self._db, use_inotify=True)
        self._db.signals['changed'].emit([media._beacon_id])

    def media_removed(self, media):
        """
        Media mountpoint removed.
        """
        for id, client, monitors in self.clients:
            client.rpc('device.removed', media.id)
        self._db.signals['changed'].emit([media._beacon_id])
        if media.crawler:
            media.crawler.stop()
            media.crawler = None

    # -------------------------------------------------------------
    # client RPC API
    # -------------------------------------------------------------

    @kaa.rpc.expose()
    def register_inverted_index(self, name, min=None, max=None, split=None, ignore=None):
        """
        Register new inverted index. The basics are already in the db by the
        __init__ function of this class.
        """
        return self._db.register_inverted_index(name, min, max, split, ignore)

    @kaa.rpc.expose()
    def register_file_type_attrs(self, type_name, indexes=[], **attrs):
        """
        Register new attrs and types for files. The basics are already
        in the db by the __init__ function of this class.
        """
        return self._db.register_object_type_attrs(type_name, indexes, **attrs)

    @kaa.rpc.expose()
    def register_track_type_attrs(self, type_name, indexes=[], **attrs):
        """
        Register new attrs and types for tracks. The basics are already
        in the db by the __init__ function of this class.
        """
        type_name = 'track_%s' % type_name
        return self._db.register_object_type_attrs(type_name, indexes, **attrs)

    @kaa.rpc.expose()
    def delete_media(self, id):
        """
        Delete media with the given id.
        """
        self._db.delete_media(id)

    @kaa.rpc.expose(add_client=True)
    def db_lock(self, client_id):
        """
        Lock the database so clients can read
        """
        self._db.read_lock.lock(client_id)

    @kaa.rpc.expose(add_client=True)
    def db_unlock(self, client_id):
        """
        Unlock the database again
        """
        self._db.read_lock.unlock(client_id)

    @kaa.rpc.expose(coroutine=True)
    def monitor_directory(self, directory):
        """
        Monitor a directory in the background. One directories with a monitor
        running will update running query monitors.
        """
        if not os.path.isdir(directory):
            log.warning("%s is not a directory." % directory)
            yield False
        # TODO: check if directory is already being monitored.
        directory = os.path.realpath(directory)
        data = yield self._db.query(filename = directory)
        items = []
        for i in data.ancestors:
            if i._beacon_id:
                break
            items.append(i)
        while items:
            async = parser.parse(self._db, items.pop())
            if isinstance(async, kaa.InProgress):
                yield async
        log.info('monitor %s on %s', directory, data._beacon_media)
        data._beacon_media.crawler.append(data)

    @kaa.rpc.expose(coroutine=True)
    def monitor_add(self, client_id, request_id, query):
        """
        Create a monitor object to monitor a query for a client.
        """
        log.info('add monitor %s', query)
        if query and 'parent' in query:
            type, id = query['parent']
            result = yield self._db.query(type=type, id=id)
            query['parent'] = result[0]

        for id, client, monitors in self.clients:
            if id == client_id:
                break
        else:
            raise AttributeError('Unknown client id %s', client_id)
        m = Monitor(client, self._db, self, request_id, query)
        monitors.append(m)

    @kaa.rpc.expose()
    def monitor_remove(self, client_id, request_id):
        """
        Create a monitor object to monitor a query for a client.
        """
        log.info('remove monitor %s', client_id)
        for id, client, monitors in self.clients:
            if id == client_id:
                break
        else:
            raise AttributeError('Unknown client id %s', client_id)
        log.debug('remove monitor')
        for m in monitors:
            if m.id == request_id:
                m.stop()
                monitors.remove(m)
                return None
        log.error('unable to find monitor %s:%s', client_id, request_id)

    @kaa.rpc.expose(coroutine=True)
    def item_update(self, items):
        """
        Update items from the client.
        """
        while self._db.read_lock.is_locked():
            yield self._db.read_lock.yield_unlock()
        for dbid, attributes in items:
            self._db.update_object(dbid, **attributes)
        # commit to update monitors
        self._db.commit()

    @kaa.rpc.expose(coroutine=True)
    def item_request(self, filename):
        """
        Request item data.
        """
        data = yield self._db.query(filename=filename)
        items = []
        for i in data.ancestors:
            if i._beacon_id:
                break
            items.append(i)
        while items:
            async = parser.parse(self._db, items.pop())
            if isinstance(async, kaa.InProgress):
                yield async
        yield data._beacon_data

    @kaa.rpc.expose(coroutine=True)
    def item_create(self, type, parent, **kwargs):
        """
        Create a new item.
        """
        data = yield self._db.query(id=parent)
        while self._db.read_lock.is_locked():
            yield self._db.read_lock.yield_unlock()
        yield self._db.add_object(type, parent=parent, **kwargs)

    @kaa.rpc.expose(coroutine=True)
    def item_delete(self, id):
        """
        Create a new item.
        """
        while self._db.read_lock.is_locked():
            yield self._db.read_lock.yield_unlock()
        self._db.delete_object(id)

    @kaa.rpc.expose()
    def shutdown(self):
        """
        Shutdown beacon.
        """
        sys.exit(0)

    @kaa.rpc.expose()
    def eject(self, id):
        """
        Eject media with the given id
        """
        dev = self._db.medialist.get_by_media_id(id)
        if not dev:
            log.error('eject: no device %s' % id)
            return False
        dev.eject()
