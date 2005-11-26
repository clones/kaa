# -*- coding: iso-8859-1 -*-
# -----------------------------------------------------------------------------
# util.py - Some internal helper functions
# -----------------------------------------------------------------------------
# $Id$
#
# TODO: handle all the FIXME and TODO comments inside this file and
#       add docs for functions, variables and how to use this file
#
# -----------------------------------------------------------------------------
# kaa-vfs - A virtual filesystem with metadata
# Copyright (C) 2005 Dirk Meyer
#
# First Edition: Dirk Meyer <dmeyer@tzi.de>
# Maintainer:    Dirk Meyer <dmeyer@tzi.de>
#
# Please see the file doc/CREDITS for a complete list of authors.
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

def listdir(dirname, mountpoint):

    result = []
    try:
        for file in os.listdir(dirname):
            if not file.startswith('.'):
                result.append('file://%s/%s' % (dirname, file))
    except OSError:
        result = []
    overlay = mountpoint.overlay + '/' + dirname[len(mountpoint.directory):]
    try:
        for file in os.listdir(overlay):
            if not file.startswith('.') and not os.path.isdir(overlay +'/'+ file):
                result.append('file://%s/%s' % (overlay, file))
    except OSError:
        pass
    result.sort()
    return result


def parse_attributes(metadata, type_list, attributes):
    for key in type_list[1].keys():
        if metadata and metadata.has_key(key) and metadata[key] != None:
            attributes[key] = metadata[key]
