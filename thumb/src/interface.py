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

# default .thumbnail dir
DOT_THUMBNAIL = os.path.join(os.environ['HOME'], '.thumbnails')

def create(src, size = NORMAL, destdir = DOT_THUMBNAIL, url = None):
    """
    Create a freedesktop.org thumbnail.
    """
    if not url:
        # create url to be placed in the thumbnail
        url = 'file://' + os.path.normpath(src)

    # create digest for filename
    hexdigest = md5.md5(url).hexdigest()

    if size == NORMAL:
        dest = destdir + '/normal/'
        size = (128, 128)
    else:
        dest = destdir + '/large/'
        size = (256, 256)
        
    if not os.path.isdir(dest):
        os.makedirs(dest, 0700)

    if src.lower().endswith('jpg'):
        try:
            _thumbnailer.epeg_thumbnail(src, dest + hexdigest + '.jpg', size)
            return dest + hexdigest + '.jpg'
        except IOError:
            pass
    try:
        _thumbnailer.png_thumbnail(src, dest + hexdigest + '.png', size)
        return dest + hexdigest + '.png'
    except:
        # image is broken
        dest = destdir + '/failed/kaa/'
        if not os.path.isdir(dest):
            os.makedirs(dest, 0700)
        _thumbnailer.fail_thumbnail(src, dest + hexdigest + '.png')
        return dest + hexdigest + '.png'



def check(file, size = NORMAL, destdir = DOT_THUMBNAIL, url = None):
    """
    Check if a freedesktop.org thumbnail exists. Return is either the filename,
    False when the thumbnail can't be created or None is no information is
    available.
    """
    try:
        file_stat = os.stat(file)
    except (OSError, IOError):
        # file not found
        return FAILED, ''
    
    if file_stat[stat.ST_SIZE] < 30000:
        # do not create thumbnails of small files
        return size, file

    if not url:
        # create url to be placed in the thumbnail
        url = 'file://' + os.path.normpath(file)

    # create digest for filename
    hexdigest = md5.md5(url).hexdigest()

    # directories to check
    check_list = [ ( destdir + '/normal/', NORMAL),
                   ( destdir + '/large/', LARGE ) ]

    if size == LARGE:
        check_list.reverse()

    for dest, size in check_list:
        dest = dest + hexdigest + '.'
        for ext in ('jpg', 'png'):
            try:
                if os.stat(dest + ext)[stat.ST_MTIME] < \
                       file_stat[stat.ST_MTIME]:
                    os.unlink(dest + ext)
                else:
                    return size, dest + ext
            except (OSError, IOError):
                pass

    if os.path.isfile(destdir + '/failed/kaa/' + hexdigest + '.png'):
        # failed before
        return FAILED, destdir + '/failed/kaa/' + hexdigest + '.png'

    return MISSING, ''
