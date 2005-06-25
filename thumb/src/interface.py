# -*- coding: iso-8859-1 -*-
# -----------------------------------------------------------------------------
# interface.py - Interface for thumbnailing files
# -----------------------------------------------------------------------------
# $Id$
#
# -----------------------------------------------------------------------------
# kaa-thumb - Thumbnailing module
# Copyright (C) 2005 Dirk Meyer, et al.
#
# First Edition: Dirk Meyer <dmeyer@tzi.de>
# Maintainer:    Dirk Meyer <dmeyer@tzi.de>
#
# Please see the file docs/CREDITS for a complete list of authors.
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
import md5

import _thumbnailer

# thumbnail image dir
_thumbnail_dir = os.path.join(os.environ['HOME'], '.thumbnails/large/')
if not os.path.isdir(_thumbnail_dir):
    # create the 'large' dir. Set permissions to user only. All files
    # inside should also be user only, but who cares when the dir is save?
    # Yes, I know, it's ugly :)
    os.makedirs(_thumbnail_dir, 0700)

# dir for failed thumbnails
_failed_dir = os.path.join(os.environ['HOME'], '.thumbnails/fail/kaa/')
if not os.path.isdir(_failed_dir):
    # create the 'fail' dir. Set permissions to user only. All files
    # inside should also be user only, but who cares when the dir is save?
    # Yes, I know, it's ugly :)
    os.makedirs(_failed_dir, 0700)
    

def create(src, thumbnail_dir = ''):
    """
    Create a freedesktop.org thumbnail.
    """
    if thumbnail_dir:
        dst = thumbnail_dir + '/large/'
        if not os.path.isdir(dst):
            os.makedirs(dst, 0700)
        dst = dst + md5.md5('file://' + src).hexdigest() + '.'
    else:
        dst = _thumbnail_dir + md5.md5('file://' + src).hexdigest() + '.'
    if src.lower().endswith('jpg'):
        try:
            _thumbnailer.epeg_thumbnail(src, dst + 'jpg', (256,256))
            return dst + 'jpg'
        except IOError:
            pass
    try:
        _thumbnailer.png_thumbnail(src, dst + 'png', (256,256))
        return dst + 'png'
    except:
        # image is broken
        if thumbnail_dir:
            dst = thumbnail_dir + '/failed/kaa/'
            if not os.path.isdir(dst):
                os.makedirs(dst, 0700)
            dst = dst + md5.md5('file://' + src).hexdigest() + '.png'
        else:
            dst = _failed_dir + md5.md5('file://' + src).hexdigest() + '.png'
        _thumbnailer.fail_thumbnail(src, dst)
        return dst



def check(file, thumbnail_dir = ''):
    """
    Check if a freedesktop.org thumbnail exists. Return is either the filename,
    False when the thumbnail can't be created or None is no information is
    available.
    """
    if thumbnail_dir:
        dst = thumbnail_dir + '/large/' + \
              md5.md5('file://' + file).hexdigest() + '.'
    else:
        dst = _thumbnail_dir + md5.md5('file://' + file).hexdigest() + '.'
    if os.path.isfile(dst + 'jpg'):
        return dst + 'jpg'
    if os.path.isfile(dst + 'png'):
        return dst + 'png'
    if thumbnail_dir:
        dst = thumbnail_dir + '/failed/kaa/'
        dst = dst + md5.md5('file://' + file).hexdigest() + '.'
    else:
        dst = _failed_dir + md5.md5('file://' + file).hexdigest() + '.png'
    if os.path.isfile(dst):
        return False
    return None
