# -*- coding: iso-8859-1 -*-
# -----------------------------------------------------------------------------
# __init__.py - interface to kaa.beacon
# -----------------------------------------------------------------------------
# $Id$
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

# python imports
import os
import logging

# kaa imports
import kaa
import kaa.rpc
import kaa.utils

# kaa.beacon imports
from version import VERSION
from client import Client

from thumbnail import Thumbnail
from item import Item
from file import File
from media import Media
from kaa.db import *
from query import register_filter, wrap, Query

# get logging object
log = logging.getLogger('beacon')

# connected client object
_client = None
# signals of the client, only valid after calling connect()
signals = {}

debugging = """
------------------------------------------------------------------------
The system was unable to connect to beacon-daemon. Please check if the
beacon daemon is running properly. If beacon-daemon processes exist,
please kill them. Start beacon in an extra shell for better debugging.
beacon-daemon --verbose all --fg
------------------------------------------------------------------------
"""

class ConnectError(Exception):
    pass

def require_connect():
    """
    Make sure the client is connected to the server. If the server is
    not running, ConnectError will be raised. A function decorated
    with require_connect will always return an InProgress.
    """
    def decorator(func):
        @kaa.utils.wraps(func)
        @kaa.coroutine()
        def newfunc(*args, **kwargs):
            global _client
            global signals
            if not _client:
                _client = Client()
                signals = _client.signals
            if not _client.connected:
                try:
                    # wait for next connect
                    if _client.channel.status != kaa.rpc.CONNECTED:
                        # this may raise an exception
                        yield kaa.inprogress(_client.channel)
                    if not _client.connected:
                        yield kaa.inprogress(signals['connect'])
                    log.info('beacon connected')
                except Exception, e:
                    raise ConnectError(e)
            result = func(*args, **kwargs)
            if isinstance(result, kaa.InProgress):
                result = yield result
            yield result
        newfunc.func_name = func.func_name
        return newfunc
    return decorator

@require_connect()
def connect():
    """
    Connect to the beacon. A beacon server must be running. This function will
    raise an exception if the client is not connected and the server is not
    running for a connect. Returns InProgress.
    """
    pass

def launch(autoshutdown=False, verbose='none'):
    """
    Lauch a beacon server and connect to it.  beacon-daemon should be in
    $PATH.

    :param autoshutdown: shutdown server when no client is connected anymore
    :param verbose: verbose level for the server log
    :returns: an InProgress object
    """
    beacon = os.path.dirname(__file__).split('/python')[0], '../bin/beacon-daemon'
    beacon = os.path.normpath(os.path.join(*beacon))
    if not os.path.isfile(beacon):
        # we hope it is in the PATH somewhere
        beacon = 'beacon-daemon'
    cmd = '%s --verbose=%s' % (beacon, verbose)
    if autoshutdown:
        cmd += ' --autoshutdown'
    if os.system(cmd):
        log.error('unable to connect to beacon-daemon %s', debugging)
        raise ConnectError('Unable to connect to beacon-daemon')
    return connect()

@require_connect()
def query(**args):
    """
    Query the database. This function will raise an exception if the
    client is not connected and the server is not running for a
    connect.  The function returns an InProgress object with a Query
    object as result.
    """
    return _client.query(**args)

@require_connect()
def get(filename):
    """
    Get object for the given filename. This function will raise an
    exception if the client is not connected and the server is not
    running for a connect. The function returns an InProgress object
    with a File object as result.
    """
    return _client.get(filename)

@require_connect()
def monitor(directory):
    """
    Monitor a directory with subdirectories for changes. This is done in
    the server and will keep the database up to date.

    :param directory: directory path name
    """
    return _client.monitor(directory)

@require_connect()
def list_media(available=True):
    """
    List all media objects.
    """
    return _client.list_media(available)

@require_connect()
def delete_media(id):
    """
    Delete media with the given id.

    :param id: Media object ID
    """
    return _client.delete_media(id)

@require_connect()
def add_item(url, type, parent, **kwargs):
    """
    Add an item to the database. This function can be used to add an Item
    as subitem to another. You can not add files that do not exist to a
    directory, but it is possible to add an Item with a http url to a directory
    or a meta item with http items as children.
    """
    return _client.add_item(url, type, parent, **kwargs)

@require_connect()
def register_inverted_index(name, min=None, max=None, split=None, ignore=None):
    """
    Registers a new inverted index with the database.  An inverted index
    maps arbitrary terms to objects and allows you to query based on one
    or more terms.  If the inverted index already exists with the given
    parameters, no action is performed.  See kaa.db for details.
    """
    _client.rpc('register_inverted_index', name, min, max, split, ignore)

@require_connect()
def register_file_type_attrs(type_name, indexes=[], **attrs):
    """
    Registers one or more object attributes and/or multi-column
    indexes for the given type name.  This function modifies the
    database as needed to accommodate new indexes and attributes,
    either by creating the object's tables (in the case of a new
    object type) or by altering the object's tables to add new columns
    or indexes.
    """
    _client.rpc('register_file_type_attrs', type_name, indexes, **attrs)

@require_connect()
def register_track_type_attrs(type_name, indexes=[], **attrs):
    """
    Register new attrs and types for tracks. See L{register_file_type_attrs}
    for details. The only difference between this two functions is that this
    adds track\_ to the type name.
    """
    _client.rpc('register_track_type_attrs', type_name, indexes, **attrs)

@require_connect()
def get_db_info():
    """
    Gets statistics about the database.

    :returns: basic database information
    """
    return _client._db.get_db_info()
