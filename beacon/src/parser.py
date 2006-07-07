# -*- coding: iso-8859-1 -*-
# -----------------------------------------------------------------------------
# parser.py - Parser for metadata
# -----------------------------------------------------------------------------
# $Id$
#
# TODO: add more data to the item (cover) and start thumbnailing
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

# kaa imports
from kaa.strutils import str_to_unicode
import kaa.metadata
import kaa.imlib2
import thumbnail

# get logging object
log = logging.getLogger('beacon.parser')

def parse(db, item, store=False):
    log.debug('check %s', item.url)
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
                log.info('up-to-date %s' % item)
                return

    log.info('scan %s' % item)
    attributes = { 'mtime': mtime }
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
    # FIXME: when beacon is stopped after the parsing is saved and before the
    # thumbnail generation is complete, the thumbnails won't be created
    # before the user needs them. But he can request the thumbnails himself.

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
            if not t.exists():
                img = kaa.imlib2.open_from_memory(metadata.get('thumbnail'))
                # only store the normal version
                t.set(img, thumbnail.NORMAL)

    else:
        base = os.path.splitext(item.filename)[0]
        for ext in ('.jpg', '.png'):
            if os.path.isfile(base + ext):
                attributes['image'] = base + ext
                break
            if os.path.isfile(item.filename + ext):
                attributes['image'] = item.filename + ext
                break

        if metadata and metadata.get('raw_image'):
            attributes['thumbnail'] = item.filename
            t = thumbnail.Thumbnail(item.filename)
            if not t.exists():
                t.image = kaa.imlib2.open_from_memory(metadata['raw_image'])

    if attributes.get('image'):
        t = thumbnail.Thumbnail(attributes.get('image'))
        if not t.get(thumbnail.LARGE):
            t.create(thumbnail.LARGE)
        if not attributes.get('thumbnail'):
            attributes['thumbnail'] = attributes.get('image')
        
    # add kaa.metadata results, the db module will add everything known
    # to the db.
    attributes['metadata'] = metadata

    # TODO: do some more stuff here:
    # - add subitems like dvd tracks for dvd images on hd

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
                      **attributes)
    if store:
        db.commit()
    return True
