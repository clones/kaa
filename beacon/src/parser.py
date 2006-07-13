# -*- coding: iso-8859-1 -*-
# -----------------------------------------------------------------------------
# parser.py - Parser for metadata
# -----------------------------------------------------------------------------
# $Id$
#
# Note: this file is only imported by the server
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


# Python imports
import os
import stat
import logging
import time

# kaa imports
from kaa.strutils import str_to_unicode
import kaa.metadata
import kaa.imlib2
import thumbnail

# get logging object
log = logging.getLogger('beacon.parser')

# load extra plugins in the plugins subdirectory
extention_plugins = {}

def load_plugins(db):
    """
    Load external plugins. Called by server on creating. The db object
    is from kaa.beacon, not kaa.db.
    """
    for plugin in os.listdir(os.path.join(os.path.dirname(__file__), 'plugins')):
        if not plugin.endswith('.py') or plugin == '__init__.py':
            continue
        exec('import plugin.%s' % plugin)
        plugin.create(db, register)
        

def register(ext, function):
    """
    Register a plugin to the parser. This function gets called by the
    external plugins in the plugins subdir.
    """
    if not ext in extention_plugins:
        extention_plugins[ext] = []
    extention_plugins[ext].append(function)


def parse(db, item, store=False):
    """
    Main beacon parse function.
    """
    mtime = item._beacon_mtime()
    if mtime == None:
        log.warning('no mtime, skip %s' % item)
        return
    parent = item._beacon_parent
    if not parent:
        log.warning('no parent, skip %s' % item)
        return

    if not parent._beacon_id:
        # There is a parent without id, update the parent now. We know that the
        # parent should be in the db, so commit and it should work
        db.commit()
        if not parent._beacon_id:
            # Still not in the database? Well, this should never happen but does
            # when we use some strange softlinks around the filesystem. So in
            # that case we need to scan the parent, too.
            parse(db, parent, True)
        if not parent._beacon_id:
            # This should never happen
            raise AttributeError('parent for %s has no dbid' % item)
    if item._beacon_data['mtime'] == mtime:
        log.debug('up-to-date %s' % item)
        return

    if not item._beacon_id:
        # New file, maybe already added? Do a small check to be sure we don't
        # add the same item to the db again.
        data = db.get_object(item._beacon_data['name'], parent._beacon_id)
        if data:
            item._beacon_database_update(data)
            if item._beacon_data['mtime'] == mtime:
                log.debug('up-to-date %s' % item)
                return

    log.info('scan %s' % item)

    attributes = { 'mtime': mtime }
    # FIXME: add force parameter from config file:
    # - always force (slow but best result)
    # - never force (faster but maybe wrong)
    # - only force on media 1 (good default)
    metadata = kaa.metadata.parse(item.filename)
    if metadata and metadata['media'] and \
             db.object_types().has_key(metadata['media']):
        type = metadata['media']
    elif item._beacon_isdir:
        type = 'dir'
    else:
        type = 'file'

    if item._beacon_id and type != item._beacon_id[0]:
        # The item changed its type. Adjust the db
        data = db.update_object_type(item._beacon_id, type)
        if not data:
            log.warning('item to change not in the db anymore, try to find it')
            data = db.get_object(item._beacon_data['name'], parent._beacon_id)
        log.info('change item %s to %s' % (item._beacon_id, type))
        item._beacon_database_update(data)


    # Thumbnail / Cover / Image stuff.
    #
    # Note: when beacon is stopped after the parsing is saved and before the
    # thumbnail generation is complete, the thumbnails won't be created
    # before the user needs them. But he can request the thumbnails himself.
    #
    # FIXME: add media .thumbnail dir if needed

    if type == 'dir':
        for cover in ('cover.jpg', 'cover.png'):
            if os.path.isfile(item.filename + cover):
                attributes['image'] = item.filename + cover
                break
        # TODO: do some more stuff here:
        # Audio directories may have a different cover if there is only
        # one jpg in a dir of mp3 files or a files with 'front' in the name.
        # They need to be added here as special kind of cover

    elif type == 'image':
        attributes['image'] = item.filename

        if metadata and metadata.get('thumbnail'):
            t = thumbnail.Thumbnail(item.filename)
            if not t.exists(check_mtime=True):
                # only store the normal version
                try:
                    img = kaa.imlib2.open_from_memory(metadata.get('thumbnail'))
                    t.set(img, thumbnail.NORMAL)
                except Exception:
                    log.error('image thumbnail')

    else:
        base = os.path.splitext(item.filename)[0]
        for ext in ('.jpg', '.png'):
            if os.path.isfile(base + ext):
                attributes['image'] = base + ext
                break
            if os.path.isfile(item.filename + ext):
                attributes['image'] = item.filename + ext
                break

        if type == 'video' and not attributes.get('image') and \
               thumbnail.support_video:
            attributes['image'] = item.filename

        if metadata and metadata.get('thumbnail') and not \
               attributes.get('image'):
            attributes['image'] = item.filename
            t = thumbnail.Thumbnail(item.filename)
            if not t.exists(check_mtime=True):
                try:
                    t.image = kaa.imlib2.open_from_memory(metadata['thumbnail'])
                except ValueError:
                    log.error('raw thumbnail')

    if attributes.get('image'):
        t = thumbnail.Thumbnail(attributes.get('image'))
        if not t.get(thumbnail.LARGE, check_mtime=True):
            t.create(thumbnail.LARGE)

    # add kaa.metadata results, the db module will add everything known
    # to the db.
    attributes['metadata'] = metadata

    # TODO: do some more stuff here:
    # - add subitems like dvd tracks for dvd images on hd

    # now call extention plugins
    ext = os.path.splitext(item.filename)[1]
    if ext in extention_plugins:
        for function in extention_plugins[ext]:
            function(item, attributes)

    # Note: the items are not updated yet, the changes are still in
    # the queue and will be added to the db on commit.

    if item._beacon_id:
        # Update
        db.update_object(item._beacon_id, **attributes)
        item._beacon_data.update(attributes)
    else:
        # Create. Maybe the object is already in the db. This could happen
        # because of bad timing but should not matter. Only one entry will be
        # there after the next update
        db.add_object(type, name=item._beacon_data['name'],
                      parent=parent._beacon_id,
                      overlay=item._beacon_overlay,
                      callback=item._beacon_database_update,
                      media=item._beacon_media._beacon_id[1],
                      **attributes)
    if store:
        db.commit()
    return True
