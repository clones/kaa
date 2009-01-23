# -*- coding: iso-8859-1 -*-
# -----------------------------------------------------------------------------
# client.py - Client interface for Beacon
# -----------------------------------------------------------------------------
# $Id$
#
# This is the client interface to beacon. The server needs to be running.
# To use the server a Client object must be created. Once created, it is
# possible to start a query on the client.
#
# -----------------------------------------------------------------------------
# kaa.beacon - A virtual filesystem with metadata
# Copyright (C) 2006-2009 Dirk Meyer
#
# First Edition: Dirk Meyer <dischi@freevo.org>
# Maintainer:    Dirk Meyer <dischi@freevo.org>
#
# Please see the file AUTHORS for a complete list of authors.
#
# This library is free software; you can redistribute it and/or modify
# it under the terms of the GNU Lesser General Public License version
# 2.1 as published by the Free Software Foundation.
#
# This library is distributed in the hope that it will be useful, but
# WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
# Lesser General Public License for more details.
#
# You should have received a copy of the GNU Lesser General Public
# License along with this library; if not, write to the Free Software
# Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA
# 02110-1301 USA
#
# -----------------------------------------------------------------------------


# Python imports
import os
import logging

# kaa imports
import kaa
from kaa.utils import property
import kaa.rpc, kaa.rpc2
from kaa.weakref import weakref

# kaa.beacon imports
from db import Database
from query import Query
from item import Item
import thumbnail

# get logging object
log = logging.getLogger('beacon')

DISCONNECTED = 'disconnected'
CONNECTED    = 'connected'
SHUTDOWN     = 'shutdown'

class Client(object):
    """
    Beacon client. This client uses the db read only and needs a server on
    the same machine doing the file scanning and changing of the db.
    """
    def __init__(self):
        self._db = None

        self.signals = {
            'connect'   : kaa.Signal(),
            'disconnect': kaa.Signal(),
            'media.add' : kaa.Signal(),
            'media.remove': kaa.Signal()
        }

        # internal list of active queries
        self._queries = []
        # internal list of items to update
        self._changed = []
        # add ourself to shutdown handler for correct disconnect
        kaa.main.signals['shutdown'].connect(self._shutdown)
        self.status = DISCONNECTED
        self.channel = kaa.rpc2.connect('beacon', retry=1)
        self.channel.signals["closed"].connect(self._disconnected)
        self.channel.register(self)
        self.rpc = self.channel.rpc

    def __repr__(self):
        """
        Convert object to string (usefull for debugging)
        """
        return '<beacon.Client>'


    # -------------------------------------------------------------------------
    # Public API
    # -------------------------------------------------------------------------

    @kaa.coroutine()
    def get(self, filename):
        """
        Return an object for the given filename.
        """
        filename = os.path.realpath(filename)
        if not os.path.exists(filename):
            raise OSError('no such file or directory %s' % filename)
        q = Query(self, filename=filename)
        yield kaa.inprogress(q)
        yield q.get()


    @kaa.coroutine()
    def query(self, **query):
        """
        Query the database.
        """
        result = Query(self, **query)
        self._queries.append(weakref(result))
        yield kaa.inprogress(result)
        yield result


    def add_item(self, url, type, parent, **kwargs):
        """
        Add non-file item item.
        """
        if self.status == DISCONNECTED:
            raise RuntimeError('client not connected')
        if isinstance(url, unicode):
            url = kaa.unicode_to_str(url)
        if url.find('://') > 0:
            kwargs['scheme'] = url[:url.find('://')]
        kwargs['name'] = url
        i = Item(None, url, kwargs, parent, parent._beacon_media)
        rpc = self.rpc('item.create', type=type, parent=parent._beacon_id, **kwargs)
        rpc.connect(i._beacon_database_update)
        return i


    def delete_item(self, item):
        """
        Delete non-file item item.
        """
        if self.status == DISCONNECTED:
            raise RuntimeError('client not connected')
        self.rpc('item.delete', item._beacon_id)


    @property
    def connected(self):
        """
        Return if the client is connected to a server
        """
        return self.status == CONNECTED


    def monitor(self, directory):
        """
        Monitor a directory with subdirectories for changes. This is done in
        the server and will keep the database up to date.
        """
        self.rpc('monitor.directory', directory)


    @kaa.coroutine()
    def list_media(self):
        result = []
        media = yield self.query(type='media', media='ignore')
        for pos, m in enumerate(media):
            m = dict(m)
            m['object'] = self._db.medialist.get_by_beacon_id(('media', m['id']))
            result.append(m)
        yield result

    def delete_media(self, id):
        """
        Delete media with the given id.
        """
        self.rpc('db.media.delete', id)


    # -------------------------------------------------------------------------
    # Server connect / disconnect / reconnect handling
    # -------------------------------------------------------------------------

    def _disconnected(self):
        if self.status != CONNECTED:
            return
        log.info('disconnected from beacon server')
        self.status = DISCONNECTED
        self.signals['disconnect'].emit()


    def _shutdown(self):
        """
        Disconnect from the server.
        """
        self.status = SHUTDOWN
        for q in self._queries:
            if q != None:
                q._beacon_monitoring = False
        self._queries = []
        self.rpc = None
        self._db = None


    # -------------------------------------------------------------------------
    # Media Callback API
    # -------------------------------------------------------------------------

    def eject(self, dev):
        if not self.status == CONNECTED:
            return False
        return self.rpc('media.eject', dev.id)


    # -------------------------------------------------------------------------
    # Internal API
    # -------------------------------------------------------------------------

    def _beacon_update(self, item):
        """
        Update item in next main loop interation.
        """
        if not self.status == CONNECTED:
            return
        if not item._beacon_id:
            # Item has no beacon id, request the data before
            # schedule the update.
            item.scan().connect(self._beacon_update, item).ignore_caller_args = True
            return
        if not self._changed:
            # register timer to do the changes
            kaa.OneShotTimer(self._beacon_update_all).start(0.1)
        self._changed.append(item)


    def _beacon_update_all(self, item=None):
        """
        Update all items waiting.
        """
        if not self.status == CONNECTED:
            return
        # do the update now
        items = []
        for i in self._changed:
            # we have a valid item with id thanks to _beacon_update
            items.append((i._beacon_id, i._beacon_changes))
            i._beacon_changes = {}
        self._changed = []
        self.rpc('item.update', items)


    @kaa.coroutine()
    def _beacon_media_information(self, media):
        """
        Get some basic media information.
        (similar function in server)
        """
        # we have to wait until we are sure that the db is free for
        # read access or the sqlite client will find a lock and waits
        # some time until it tries again. That time is too long, it
        # can take up to two seconds.
        yield self.rpc('db.lock')
        try:
            yield self._db.query_media(media)
        finally:
            self.rpc('db.unlock')


    def _beacon_parse(self, item):
        """
        Parse the item, returns InProgress.
        """
        if not self.connected:
            return False
        return self.rpc('item.request', item.filename)


    # -------------------------------------------------------------------------
    # Server callbacks
    # -------------------------------------------------------------------------

    @kaa.rpc.expose('connect')
    @kaa.coroutine()
    def _connected(self, id, database, media):
        """
        Callback to pass the database information to the client.
        """
        # read only version of the database
        self._db = Database(database)
        # connect to server notifications
        self.id = id
        new_media = []
        self._db.medialist.connect(self)
        for id, prop in media:
            # in the client medialist.add has to lock the db
            # and needs the db.lock rpc which will always result
            # in returning an InProgress object.
            m = yield self._db.medialist.add(id, prop)
            new_media.append(m)
        self.status = CONNECTED
        self.signals['connect'].emit()
        # reconnect query monitors
        for query in self._queries[:]:
            if query == None:
                self._queries.remove(query)
                continue
            if query._beacon_monitoring:
                query._beacon_monitoring = False
                query.monitor()
        for m in new_media:
            if not m.mountpoint == '/':
                self.signals['media.add'].emit(m)
        # FIXME: if this fails we will never notice
        yield thumbnail.connect()


    @kaa.rpc.expose('notify')
    def notify(self, id, msg, *args):
        """
        Internal notification callback from the server. The Monitor does not
        has a reference to the Query because this would result in circular
        dependencies. So this function is needed to find the correct Query
        for a request.
        """
        for query in self._queries[:]:
            if query == None:
                self._queries.remove(query)
                continue
            if not query.id == id:
                continue
            if msg == 'progress':
                return query.signals['progress'].emit(*args)
            if msg == 'changed':
                return query._beacon_callback_changed(*args)
            if msg == 'checked':
                return query.signals['up-to-date'].emit()
            log.error('Error: unknown message from server: %s' % msg)
            return
        log.error('query %s not found', id)


    @kaa.rpc.expose('device.changed')
    def media_changed(self, id, prop):
        """
        Notification that the media with the given id changed.
        """
        if self._db.medialist.get_by_media_id(id):
            # Update can take a while but it should not matter here.
            # The InProgress object can be ignored
            self._db.medialist.get_by_media_id(id)._beacon_update(prop)
            return
        # Adding a media always returns an InProgress object. Attach
        # sending the signal to the InProgress return.
        async = self._db.medialist.add(id, prop)
        async.connect_once(self.signals['media.add'].emit)


    @kaa.rpc.expose('device.removed')
    def media_removed(self, id):
        """
        Notification that the media with the given id was removed.
        """
        media = self._db.medialist.remove(id)
        if media:
            self.signals['media.remove'].emit(media)
