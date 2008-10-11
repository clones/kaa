# -*- coding: iso-8859-1 -*-
# -----------------------------------------------------------------------------
# __init__.py - interface to kaa.beacon
# -----------------------------------------------------------------------------
# $Id$
#
# -----------------------------------------------------------------------------
# kaa.beacon - A virtual filesystem with metadata
# Copyright (C) 2006-2007 Dirk Meyer
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

"""
kaa.beacon
==========

@group Internal Classes: Thumbnail, Item, File, Query, Media
@group Server: connect, launch
@group Query: query, get, monitor, register_filter, wrap
@group Media Handling: list_media, delete_media
@group Database Manipulation: add_item, register_inverted_index,
    register_file_type_attrs, register_track_type_attrs, get_db_info
@group Thumbnailing: THUMBNAIL_NORMAL, THUMBNAIL_LARGE
@group kaa.db Variables: ATTR_SIMPLE, ATTR_SEARCHABLE, ATTR_IGNORE_CASE, ATTR_INDEXED,
    ATTR_INDEXED_IGNORE_CASE, ATTR_INVERTED_INDEX
"""

__all__ = [ 'connect', 'launch', 'get', 'query', 'monitor', 'add_item', 'wrap',
            'register_file_type_attrs', 'register_track_type_attrs',
            'register_inverted_index', 'get_db_info', 'list_media', 'delete_media',
            'register_filter', 'Item', 'Query', 'Media', 'File', 'Thumbnail',
            'VERSION', 'THUMBNAIL_NORMAL', 'THUMBNAIL_LARGE', 'QExpr', 'ATTR_SIMPLE',
            'ATTR_SEARCHABLE', 'ATTR_IGNORE_CASE', 'ATTR_INDEXED',
            'ATTR_INDEXED_IGNORE_CASE', 'ATTR_INVERTED_INDEX' ]

# python imports
import os
import logging
import time

# kaa imports
import kaa

# kaa.beacon imports
from version import VERSION
from client import Client, ConnectError
import thumbnail
# FIXME: remove THUMBNAIL_NORMAL and THUMBNAIL_LARGE and replace code
# using it with Thumbnail.LARGE and Thumbnail.NORMAL
from thumbnail import NORMAL as THUMBNAIL_NORMAL
from thumbnail import LARGE as THUMBNAIL_LARGE
from thumbnail import Thumbnail
from item import Item
from file import File
from version import VERSION
from media import Media
from kaa.db import *

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

def connect():
    """
    Connect to the beacon. A beacon server must be running. This function will
    raise an exception if the client is not connected and the server is not
    running for a connect.
    """
    global _client
    global signals

    if _client:
        return _client

    _client = Client()
    try:
        thumbnail.connect()
    except RuntimeError:
        # It was possible to connect to the beacon server but not
        # to the thumbnailer. Something is very wrong.
        log.error('unable to connect to beacon-daemon %s', debugging)
        raise ConnectError('Unable to connect to beacon-daemon')
    signals = _client.signals
    log.info('beacon connected')
    return _client

def launch(autoshutdown=False, verbose='none'):
    """
    Lauch a beacon server and connect to it.

    :param autoshutdown: shutdown server when no client is connected anymore
    :param verbose: verbose level for the server log
    """
    beacon = os.path.dirname(__file__), '../../../../../bin/beacon-daemon'
    beacon = os.path.realpath(os.path.join(*beacon))
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

def query(**args):
    """
    Query the database. This function will raise an exception if the
    client is not connected and the server is not running for a
    connect.  The function returns an InProgress object with a Query
    object as result.
    """
    if not _client:
        connect()
    return _client.query(**args)

def get(filename):
    """
    Get object for the given filename. This function will raise an
    exception if the client is not connected and the server is not
    running for a connect. The function returns an InProgress object
    with a File object as result.
    """
    if not _client:
        connect()
    return _client.get(filename)

def monitor(directory):
    """
    Monitor a directory with subdirectories for changes. This is done in
    the server and will keep the database up to date.

    @param directory: directory path name
    """
    if not _client:
        connect()
    return _client.monitor(directory)

def list_media():
    """
    List all media objects.

    @returns: list of the available media
    @rtype: list of L{Media}
    """
    if not _client:
        connect()
    while not _client.is_connected():
        kaa.main.step()
    return _client._db.medialist

def delete_media(id):
    """
    Delete media with the given id.

    @param id: Media object ID
    """
    if not _client:
        connect()
    while not _client.is_connected():
        kaa.main.step()
    return _client.delete_media(id)

def add_item(url, type, parent, **kwargs):
    """
    Add an item to the database. This function can be used to add an Item
    as subitem to another. You can not add files that do not exist to a
    directory, but it is possible to add an Item with a http url to a directory
    or a meta item with http items as children.

    @param url: url of the Item, can not be file:
    @param type: item type
    @param parent: parent item
    @param kwargs: addition keyword/value arguments for the db
    @returns: new created item
    @rtype: L{Item}
    """
    if not _client:
        connect()
    return _client.add_item(url, type, parent, **kwargs)

def register_inverted_index(name, min=None, max=None, split=None, ignore=None):
    """
    Registers a new inverted index with the database.  An inverted index
    maps arbitrary terms to objects and allows you to query based on one
    or more terms.  If the inverted index already exists with the given
    parameters, no action is performed.  See kaa.db for details.
    """
    if not _client:
        connect()
    return _client.register_inverted_index(name, min, max, split, ignore)

def register_file_type_attrs(type_name, indexes=[], **attrs):
    """
    Registers one or more object attributes and/or multi-column
    indexes for the given type name.  This function modifies the
    database as needed to accommodate new indexes and attributes,
    either by creating the object's tables (in the case of a new
    object type) or by altering the object's tables to add new columns
    or indexes.
    """
    if not _client:
        connect()
    return _client.register_file_type_attrs(type_name, indexes, **attrs)

def register_track_type_attrs(type_name, indexes=[], **attrs):
    """
    Register new attrs and types for tracks. See L{register_file_type_attrs}
    for details. The only difference between this two functions is that this
    adds track\_ to the type name.
    """
    if not _client:
        connect()
    return _client.register_track_type_attrs(type_name, indexes, **attrs)

def get_db_info():
    """
    Gets statistics about the database.

    @return: basic database information
    """
    if not _client:
        connect()
    return _client.get_db_info()

# import some more functions and classes we expose to the API
# It is done at the end of this file to force a better order of the
# functions for epydoc
from query import register_filter, wrap, Query
