# -*- coding: iso-8859-1 -*-
# -----------------------------------------------------------------------------
# server.py - Server interface for Beacon
# -----------------------------------------------------------------------------
# $Id$
#
# -----------------------------------------------------------------------------
# kaa.beacon.server - A virtual filesystem with metadata
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


# Python imports
import os
import sys
import logging

# kaa imports
import kaa.rpc
from kaa.weakref import weakref
from kaa.notifier import OneShotTimer, Timer, Callback

# kaa.beacon imports
from kaa.beacon.db import *
from kaa.beacon.media import medialist

# kaa.beacon server imports
import parser
import hwmon
from monitor import Monitor
from crawl import Crawler
from config import config

# get logging object
log = logging.getLogger('beacon.server')


class Server(object):
    """
    Server for the virtual filesystem to handle write access to the db and
    scanning / monitoring of queries.
    """
    def __init__(self, dbdir):
        log.info('start beacon')
        try:
            self.ipc = kaa.rpc.Server('beacon')
        except IOError, e:
            kaa.beacon.thumbnail.thumbnail.disconnect()
            log.error('beacon: %s' % e)
            time.sleep(0.1)
            sys.exit(0)

        self.ipc.signals['client_connected'].connect(self.client_connect)
        self.ipc.connect(self)

        self._dbdir = dbdir
        self._db = Database(dbdir, None)
        self._next_client = 0

        self._db.register_object_type_attrs("dir",
            image_from_items = (bool, ATTR_SIMPLE),
            artist = (unicode, ATTR_SIMPLE),
            album = (unicode, ATTR_SIMPLE),
            length = (int, ATTR_SIMPLE))

        # files

        self.register_file_type_attrs("video",
            title = (unicode, ATTR_KEYWORDS | ATTR_IGNORE_CASE),
            width = (int, ATTR_SIMPLE),
            height = (int, ATTR_SIMPLE),
            length = (int, ATTR_SIMPLE))

        self.register_file_type_attrs("audio",
            title = (unicode, ATTR_KEYWORDS | ATTR_IGNORE_CASE),
            artist = (unicode, ATTR_KEYWORDS | ATTR_INDEXED | ATTR_IGNORE_CASE),
            album = (unicode, ATTR_KEYWORDS | ATTR_IGNORE_CASE),
            genre = (unicode, ATTR_INDEXED | ATTR_IGNORE_CASE),
            samplerate = (int, ATTR_SIMPLE),
            length = (int, ATTR_SIMPLE),
            bitrate = (int, ATTR_SIMPLE),
            trackno = (int, ATTR_SIMPLE))

        self.register_file_type_attrs("image",
            width = (int, ATTR_SEARCHABLE),
            height = (int, ATTR_SEARCHABLE),
            comment = (unicode, ATTR_KEYWORDS | ATTR_IGNORE_CASE),
            rotation = (int, ATTR_SIMPLE),
            date = (unicode, ATTR_SEARCHABLE))

        # tracks for rom discs or iso files

        self.register_track_type_attrs("dvd",
            audio = (list, ATTR_SIMPLE),
            chapters = (int, ATTR_SIMPLE),
            subtitles = (list, ATTR_SIMPLE))

        self.register_track_type_attrs("vcd",
            audio = (list, ATTR_SIMPLE))

        self.register_track_type_attrs("cdda",
            title = (unicode, ATTR_KEYWORDS),
            artist = (unicode, ATTR_KEYWORDS | ATTR_INDEXED))

        # list of current clients
        self._clients = []

        # load parser plugins
        parser.load_plugins(self._db)

        config.set_filename(os.path.join(dbdir, "config"))
        config.load()
        # We need to save at this point because we may have new
        # variables now we did not have before. This is a very bad
        # way of doing this, maybe save() should check if saving makes
        # sense or the complete schema could have a checksum we can
        # compare.
        config.save()
        config.watch()

        # commit and wait for the results (there are no results,
        # this code is only used to force waiting until the db is
        # set up.
        self._db.commit()

        # give database to hwmon
        rootfs = {
            'beacon.id': 'kaa.beacon.root',
            'block.device': '',
            'volume.mount_point': '/'
        }

        hwmon.set_database(self, self._db, rootfs)
        self._db.commit()

        for dir in config.monitors:
            # FIXME: make this make generic
            self.monitor_dir(dir.replace('$(HOME)', os.environ.get('HOME')))


    def client_connect(self, client):
        """
        Connect a new client to the server.
        """
        client.signals['closed'].connect(self.client_disconnect, client)
        self._next_client += 1
        self._clients.append((self._next_client, client, []))
        media = []
        for m in medialist:
            media.append((m.id, m.prop))
        client.rpc('connect', self._next_client, self._dbdir, media)


    def client_disconnect(self, client):
        """
        IPC callback when a client is lost.
        """
        for client_info in self._clients[:]:
            if client == client_info[1]:
                log.info('disconnect client')
                for m in client_info[2]:
                    m.stop()
                self._clients.remove(client_info)


    def autoshutdown(self, timeout):
        """
        Start autoshutdown.
        """
        if hasattr(self, '_autoshutdown_timer'):
            return
        self._autoshutdown_timer = timeout
        Timer(self._autoshutdown, timeout).start(1)


    def _autoshutdown(self, timeout):
        """
        Timer callback for autoshutdown.
        """
        if len(self._clients) > 0:
            self._autoshutdown_timer = timeout
            return True
        self._autoshutdown_timer -= 1
        if self._autoshutdown_timer == 0:
            log.info('beacon timeout')
            sys.exit(0)
        return True


    @kaa.rpc.expose('db.register_file_type_attrs')
    def register_file_type_attrs(self, name, **kwargs):
        """
        Register new attrs and types for files. The basics are already
        in the db by the __init__ function of this class.
        """
        return self._db.register_object_type_attrs(name, **kwargs)


    @kaa.rpc.expose('db.register_track_type_attrs')
    def register_track_type_attrs(self, name, **kwargs):
        """
        Register new attrs and types for files. The basics are already
        in the db by the __init__ function of this class.
        """
        return self._db.register_object_type_attrs('track_%s' % name, **kwargs)


    @kaa.rpc.expose('monitor.directory')
    def monitor_dir(self, directory):
        """
        Monitor a directory in the background. One directories with a monitor
        running will update running query monitors.
        """
        self._db.commit()
        if not os.path.isdir(directory):
            log.warning("monitor_dir: %s is not a directory." % directory)
            return False
        # TODO: check if directory is already being monitored.

        directory = os.path.realpath(directory)
        data = self._db.query(filename = directory)
        items = []
        for i in data._beacon_tree():
            if i._beacon_id:
                break
            items.append(i)
        while items:
            parser.parse(self._db, items.pop(), store=True)
        self._db.commit()
        log.info('monitor %s on %s', directory, data._beacon_media)
        data._beacon_media.crawler.append(data)


    @kaa.rpc.expose('monitor.add')
    def monitor_add(self, client_id, request_id, query):
        """
        Create a monitor object to monitor a query for a client.
        """
        log.info('add monitor %s', query)
        if query and 'parent' in query:
            type, id = query['parent']
            query['parent'] = self._db.query(type=type, id=id)[0]

        for id, client, monitors in self._clients:
            if id == client_id:
                break
        else:
            raise AttributeError('Unknown client id %s', client_id)
        m = Monitor(client, self._db, self, request_id, query)
        monitors.append(m)


    @kaa.rpc.expose('monitor.remove')
    def monitor_remove(self, client_id, request_id):
        """
        Create a monitor object to monitor a query for a client.
        """
        log.info('remove monitor %s', client_id)
        for id, client, monitors in self._clients:
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


    def media_changed(self, media):
        """
        Media mountpoint changed or added.
        """
        for id, client, monitors in self._clients:
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
        for id, client, monitors in self._clients:
            client.rpc('device.removed', media.id)
        self._db.signals['changed'].emit([media._beacon_id])
        if media.crawler:
            media.crawler.stop()
            media.crawler = None

    @kaa.rpc.expose('item.update')
    def update(self, items):
        """
        Update items from the client.
        """
        for dbid, attributes in items:
            self._db.update_object(dbid, **attributes)
        self._db.commit()


    @kaa.rpc.expose('item.request')
    def request(self, filename):
        self._db.commit()
        data = self._db.query(filename=filename)
        items = []
        for i in data._beacon_tree():
            if i._beacon_id:
                break
            items.append(i)
        while items:
            parser.parse(self._db, items.pop(), store=True)
        self._db.commit()
        return data._beacon_data


    @kaa.rpc.expose('beacon.shutdown')
    def shutdown(self):
        sys.exit(0)


    @kaa.rpc.expose('media.eject')
    def eject(self, id):
        dev = medialist.get(id)
        if not dev:
            log.error('eject: no device %s' % id)
            return False
        dev.eject()
