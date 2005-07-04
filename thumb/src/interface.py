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

NORMAL  = 0
LARGE   = 1
FAILED  = 2
MISSING = 3

import os
import stat
import md5

import _thumbnailer

# thumbnail image dir for normal images
_normal_dir = os.path.join(os.environ['HOME'], '.thumbnails/normal/')
if not os.path.isdir(_normal_dir):
    # create the 'normal' dir. Set permissions to user only. All files
    # inside should also be user only, but who cares when the dir is save?
    # Yes, I know, it's ugly :)
    os.makedirs(_normal_dir, 0700)

# thumbnail image dir for large images
_large_dir = os.path.join(os.environ['HOME'], '.thumbnails/large/')
if not os.path.isdir(_large_dir):
    # create the 'large' dir. Set permissions to user only. All files
    # inside should also be user only, but who cares when the dir is save?
    # Yes, I know, it's ugly :)
    os.makedirs(_large_dir, 0700)

# dir for failed thumbnails
_failed_dir = os.path.join(os.environ['HOME'], '.thumbnails/fail/kaa/')
if not os.path.isdir(_failed_dir):
    # create the 'fail' dir. Set permissions to user only. All files
    # inside should also be user only, but who cares when the dir is save?
    # Yes, I know, it's ugly :)
    os.makedirs(_failed_dir, 0700)
    

def create(src, size = NORMAL, thumbnail_dir = ''):
    """
    Create a freedesktop.org thumbnail.
    """
    src = os.path.normpath(src)

    if thumbnail_dir:
        if size == NORMAL:
            dst = thumbnail_dir + '/normal/'
            size = (128, 128)
        else:
            dst = thumbnail_dir + '/large/'
            size = (256, 256)
        if not os.path.isdir(dst):
            os.makedirs(dst, 0700)
        dst = dst + md5.md5('file://' + src).hexdigest() + '.'
    else:
        if size == NORMAL:
            dst = _normal_dir + md5.md5('file://' + src).hexdigest() + '.'
            size = (128, 128)
        else:
            dst = _large_dir + md5.md5('file://' + src).hexdigest() + '.'
            size = (256, 256)

    if src.lower().endswith('jpg'):
        try:
            _thumbnailer.epeg_thumbnail(src, dst + 'jpg', size)
            return dst + 'jpg'
        except IOError:
            pass
    try:
        _thumbnailer.png_thumbnail(src, dst + 'png', size)
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



def check(file, size = NORMAL, thumbnail_dir = ''):
    """
    Check if a freedesktop.org thumbnail exists. Return is either the filename,
    False when the thumbnail can't be created or None is no information is
    available.
    """
    try:
        file_stat = os.stat(file)
    except (OSError, IOError):
        return FAILED, ''
    
    if file_stat[stat.ST_SIZE] < 30000:
        # do not create thumbnails of small files
        return size, file

    file = os.path.normpath(file)

    if thumbnail_dir:
        check_list = [ (thumbnail_dir + '/normal/', NORMAL),
                       ( thumbnail_dir + '/large/', LARGE ) ]
    else:
        check_list = [ (_normal_dir, NORMAL), ( _large_dir, LARGE ) ]

    if size == LARGE:
        check_list.reverse()

    for dir, size in check_list:
        dst = dir + md5.md5('file://' + file).hexdigest() + '.'
        for ext in ('jpg', 'png'):
            try:
                if os.stat(dst + ext)[stat.ST_MTIME] < \
                       file_stat[stat.ST_MTIME]:
                    os.unlink(dst + ext)
                else:
                    return size, dst + ext
            except (OSError, IOError):
                pass

    if thumbnail_dir:
        dst = thumbnail_dir + '/failed/kaa/'
        dst = dst + md5.md5('file://' + file).hexdigest() + '.'
    else:
        dst = _failed_dir + md5.md5('file://' + file).hexdigest() + '.png'

    if os.path.isfile(dst):
        return FAILED, ''

    return MISSING, ''
