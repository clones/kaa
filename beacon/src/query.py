# -*- coding: iso-8859-1 -*-
# -----------------------------------------------------------------------------
# query.py - Query class for the client
# -----------------------------------------------------------------------------
# $Id$
#
# -----------------------------------------------------------------------------
# kaa.beacon - A virtual filesystem with metadata
# Copyright (C) 2006-2008 Dirk Meyer
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
import copy
import logging

# kaa imports
import kaa
from kaa.utils import property

# kaa.beacon imports
from item import Item

# get logging object
log = logging.getLogger('beacon')

_query_filter = {}

def register_filter(name, function):
    """
    Register a filter for L{Query} or L{wrap} to process a list of items.

    @param name: unique name for the filter
    @param function: filter function
    """
    _query_filter[name] = function


def wrap(items, filter):
    """
    Wrap the given list of items with the given filter function

    @param items: list of items
    @param filter: name of the filter, see L{register_filter}
    """
    if not filter in _query_filter:
        raise AttributeError('unknown filter')
    return _query_filter[filter](items)


class Query(object):
    """
    Query object for the client. Created by Client.query()
    """
    NEXT_ID = 1

    def __init__(self, client, **query):
        """
        Create a Query object and start the query on the client
        """
        # FIXME: progress and up-to-date seems not used
        self.signals = kaa.Signals('changed', 'progress', 'up-to-date')
        self.id = Query.NEXT_ID
        Query.NEXT_ID += 1
        # public variables
        self._beacon_monitoring = False
        self.result = []
        # internal variables
        self._query = query
        self._client = client
        # some shortcuts from the client
        self._rpc = self._client.rpc
        # InProgress object
        self._async = kaa.InProgress()
        # start inititial query
        self._beacon_start_query(query)


    # -------------------------------------------------------------------------
    # Public API
    # -------------------------------------------------------------------------


    def __inprogress__(self):
        """
        Return InProgress object to wait for the query
        """
        return self._async


    def monitor(self, status=True):
        log.warning('query.monitor is deprectated')
        self.monitoring = status

    @property
    def monitoring(self):
        """
        Turn on/off query monitoring
        """
        return self._beacon_monitoring

    @monitoring.setter
    def monitoring(self, status)
        """
        Turn on/off query monitoring
        """
        if self._beacon_monitoring == status:
            # Nothing to do
            return
        if not self._client.is_connected():
            # If the client is not connected yet, it will do this later.
            # Rememeber that we wanted to connect
            self._beacon_monitoring = status
            return
        if status:
            query = copy.copy(self._query)
            if 'parent' in query:
                parent = query['parent']
                if not parent._beacon_id:
                    # We need the get the id first. Call the function again
                    # when there is an id.
                    parent.scan().connect(self.monitor, status)
                    return
                query['parent'] = parent._beacon_id
            self._rpc('monitor.add', self._client.id, self.id, query)
        else:
            self._rpc('monitor.remove', self._client.id, self.id)
        # Store current status
        self._beacon_monitoring = status


    def __iter__(self):
        """
        Iterate through the results.

        @returns: Iterator
        @rtype: L{Item} or L{File}
        """
        return self.result.__iter__()


    def __getitem__(self, pos):
        """
        Get a specific item in the results list.

        @returns: Item on that position in the list
        @rtype: L{Item} or L{File}
        @raises IndexError: result list is shorten than pos
        """
        return self.result[pos]


    def index(self, item):
        """
        Get index of an item in the results. This function will raise an
        exception if the item is not in the results.
        """
        return self.result.index(item)


    def __len__(self):
        """
        Get length of results.
        """
        return len(self.result)


    def get(self, filter=None):
        """
        Get the result.

        :param filter: filter function set by L{register_filter} to use on the
            result. If a filter is used the result type may be different.
        :returns: (filtered) list of Items
        """
        if filter == None:
            # no spcial filter
            return self.result
        if not filter in _query_filter:
            raise AttributeError('unknown filter')
        return _query_filter[filter](self.result)


    # -------------------------------------------------------------------------
    # Internal API
    # -------------------------------------------------------------------------

    @kaa.coroutine()
    def _beacon_start_query(self, query):
        """
        Start the database query.
        """
        if not self._client.is_connected():
            # wait until the client is connected
            # FIXME: maybe the server is not connected
            yield kaa.inprogress(self._client.signals['connect'])

        if 'parent' in query and isinstance(query['parent'], Item) and \
               not query['parent']._beacon_id:
            # The parent we want to use has no database id. This can happen for
            # new items while the scanning is still in progress. We need to
            # request the real database id and do the query when done.
            parent = query['parent']
            log.info('force data for %s', parent)
            async = parent.scan()
            if isinstance(async, kaa.InProgress):
                # Not an InProgress object if it is not file.
                yield async

        # we have to wait until we are sure that the db is free for
        # read access or the sqlite client will find a lock and waits
        # some time until it tries again. That time is too long, it
        # can take up to two seconds.
        yield self._rpc('db.lock')
        try:
            self.result = self._client._db.query(**query)
            if isinstance(self.result, kaa.InProgress):
                self.result = yield self.result
        finally:
            self._rpc('db.unlock')
        self.signals['changed'].emit()
        if not self._async.finished:
            self._async.finish(True)


    def __repr__(self):
        """
        Convert object to string (usefull for debugging)
        """
        return '<beacon.Client.Query for %s>' % self._query


    def __del__(self):
        """
        Delete monitor on object delete.
        """
        # FIXME: replace the __del__ with a weakref monitoring all
        # queries. There is already a weakref in client.py
        if self._beacon_monitoring:
            self.monitor(False)


    # -------------------------------------------------------------------------
    # Server callbacks for changes (called by client.notify)
    # -------------------------------------------------------------------------

    @kaa.coroutine()
    def _beacon_callback_changed(self, send_signal):
        """
        Changed message from server.
        """
        # we have to wait until we are sure that the db is free for
        # read access or the sqlite client will find a lock and waits
        # some time until it tries again. That time is too long, it
        # can take up to two seconds.
        yield self._rpc('db.lock')
        result = self._client._db.query(**self._query)
        if isinstance(result, kaa.InProgress):
            result = yield result
        self._rpc('db.unlock')
        if send_signal or len(self.result) != len(result):
            # The query result length is different
            self.result = result
            self.signals['changed'].emit()
            yield True
        current = self.result[:]
        for item in result:
            c = current.pop(0)
            if c._beacon_data != item._beacon_data:
                # something changed inside this item.
                if c._beacon_id != item._beacon_id or \
                       c._beacon_data.get('mtime') != \
                       item._beacon_data.get('mtime'):
                    self.result = result
                    self.signals['changed'].emit()
                    yield True
                # This item was only updated by a client
                # FIXME: we don't fire the changed signal here. Maybe we need
                # a second signal to get information about internal changes
                c._beacon_database_update(item._beacon_data)
        yield False
