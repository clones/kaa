# -*- coding: iso-8859-1 -*-
# -----------------------------------------------------------------------------
# parser.py - Parser for metadata
# -----------------------------------------------------------------------------
# $Id$
#
# Note: this file is only imported by the server
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
import stat
import logging
import time

# kaa imports
from kaa.strutils import str_to_unicode
import kaa.metadata
import kaa.imlib2

# kaa.beacon imports
from kaa.beacon import thumbnail
from kaa.beacon.utils import get_title

# get logging object
log = logging.getLogger('beacon.parser')

# load extra plugins in the plugins subdirectory
extention_plugins = {}

media_types = {
    kaa.metadata.MEDIA_AUDIO: 'audio',
    kaa.metadata.MEDIA_VIDEO: 'video',
    kaa.metadata.MEDIA_IMAGE: 'image',
    kaa.metadata.MEDIA_AV: 'video',
    kaa.metadata.MEDIA_DIRECTORY: 'dir'
}

def load_plugins(db):
    """
    Load external plugins. Called by server on creating. The db object
    is from kaa.beacon, not kaa.db.
    """
    plugindir = os.path.join(os.path.dirname(__file__), 'plugins')
    for plugin in os.listdir(plugindir):
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


def parse(db, item, store=False, check_image=False):
    """
    Main beacon parse function. Return the load this function produced:
    0 == nothing done
    1 == normal parsing
    2 == thumbnail storage
    """
    mtime = item._beacon_mtime()
    if mtime == None:
        log.warning('no mtime, skip %s' % item)
        return 0

    parent = item._beacon_parent
    if not parent:
        log.warning('no parent, skip %s' % item)
        return 0

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

    if item._beacon_data.get('mtime') == mtime:
        # The item already is in the database and the mtime is unchanged.
        # This menas we don't need to scan again, but we check if the
        # thumbnail is valid or not.
        if check_image and item._beacon_data.get('image'):
            image = item._beacon_data.get('image')
            if os.path.exists(image):
                t = thumbnail.Thumbnail(image, item._beacon_media)
                if not t.get(thumbnail.LARGE, check_mtime=True):
                    log.info('create missing image %s for %s', image, item)
                    t.create(thumbnail.LARGE, thumbnail.PRIORITY_LOW)
                return 0
            else:
                log.info('image "%s" for %s is gone, rescan', image, item)
        else:
            return 0

    if not item._beacon_id:
        # New file, maybe already added? Do a small check to be sure we don't
        # add the same item to the db again.
        data = db.get_object(item._beacon_data['name'], parent._beacon_id)
        if data:
            item._beacon_database_update(data)
            if item._beacon_data.get('mtime') == mtime:
                return 0

    t1 = time.time()

    # FIXME: add force parameter from config file:
    # - always force (slow but best result)
    # - never force (faster but maybe wrong)
    # - only force on media 1 (good default)
    metadata = kaa.metadata.parse(item.filename)
    if not metadata:
        metadata = {}

    attributes = { 'mtime': mtime, 'image': metadata.get('image') }

    if metadata.get('media') == kaa.metadata.MEDIA_DISC and \
           db.object_types().has_key(metadata.get('subtype')):
        type = metadata['subtype']
        if metadata.get('type'):
            attributes['scheme'] = '%s://' % metadata.get('type').lower()
        item._beacon_isdir = False
    elif db.object_types().has_key(media_types.get(metadata.get('media'))):
        type = media_types.get(metadata['media'])
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

    produced_load = 1

    if type == 'dir':
        attributes['image_from_items'] = False
        if not attributes.get('image'):
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

        if metadata.get('thumbnail'):
            t = thumbnail.Thumbnail(item.filename, item._beacon_media)
            if not t.exists(check_mtime=True):
                # only store the normal version
                try:
                    produced_load = 2
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
               thumbnail.SUPPORT_VIDEO:
            attributes['image'] = item.filename

        if metadata.get('thumbnail') and not \
               attributes.get('image'):
            attributes['image'] = item.filename
            t = thumbnail.Thumbnail(item.filename, item._beacon_media)
            if not t.exists(check_mtime=True):
                try:
                    produced_load = 2
                    t.image = kaa.imlib2.open_from_memory(metadata['thumbnail'])
                except ValueError:
                    log.error('raw thumbnail')

    if attributes.get('image'):
        t = thumbnail.Thumbnail(attributes.get('image'), item._beacon_media)
        if not t.get(thumbnail.LARGE, check_mtime=True):
            t.create(thumbnail.LARGE, thumbnail.PRIORITY_LOW)

    if not metadata.get('title'):
        # try to set a good title
        title = get_title(item._beacon_data['name'])
        metadata['title'] = str_to_unicode(title)

    # add kaa.metadata results, the db module will add everything known
    # to the db.
    attributes['metadata'] = metadata

    # now call extention plugins
    ext = os.path.splitext(item.filename)[1]
    if ext in extention_plugins:
        for function in extention_plugins[ext]:
            function(item, attributes)

    if item._beacon_id and item._beacon_id[0] != type:
        # the type changed, we need to delete the old entry
        log.warning('change %s to %s for %s', item._beacon_id, type, item)
        db.delete_object(item._beacon_id)
        item._beacon_id = None
        db.commit()
        
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

    if hasattr(metadata, 'tracks'):
        # The item has tracks, e.g. a dvd image on hd. Sync with the database
        # now and add the tracks.
        db.commit()
        if not metadata.get('type'):
            log.error('%s metadata has no type', item)
            return produced_load
        # delete all known tracks before adding new
        for track in db.query(parent=item):
            db.delete_object(track)
        if not 'track_%s' % metadata.get('type').lower() in \
           db.object_types().keys():
            log.error('track_%s not in database keys', metadata.get('type').lower())
            return produced_load
        type = 'track_%s' % metadata.get('type').lower()
        for track in metadata.tracks:
            db.add_object(type, name=str(track.trackno),
                               parent=item._beacon_id,
                               media=item._beacon_media._beacon_id[1],
                               mtime=0,
                               metadata=track)
        db.commit()
        
    if store:
        db.commit()

    log.info('scan %s (%0.3f)' % (item, time.time() - t1))

    return produced_load
