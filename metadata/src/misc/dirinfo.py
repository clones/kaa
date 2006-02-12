# -*- coding: iso-8859-1 -*-
# -----------------------------------------------------------------------------
# dvdinfo.py - parse dvd title structure
# -----------------------------------------------------------------------------
# $Id$
#
# TODO: update the ifomodule and remove the lsdvd parser
#
# -----------------------------------------------------------------------------
# kaa-Metadata - Media Metadata for Python
# Copyright (C) 2003-2005 Thomas Schueppel, Dirk Meyer
#
# First Edition: Dirk Meyer <dmeyer@tzi.de>
# Maintainer:    Dirk Meyer <dmeyer@tzi.de>
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

# python imports
import os
import logging
import libxml2

# kaa imports
from kaa.base.strutils import unicode_to_str
from kaa.metadata.mediainfo import MediaInfo, MEDIACORE, \
     EXTENSION_DIRECTORY, TYPE_MISC
from kaa.metadata.factory import register

# get logging object
log = logging.getLogger('metadata')


class DirInfo(MediaInfo):
    """
    Simple parser for reading a .directory file.
    """
    def __init__(self, directory):
        MediaInfo.__init__(self)

        self.media = 'directory'
        self.parse_dot_directory(directory)
        self.parse_bins(directory)


    def parse_dot_directory(self, directory):
        """
        search .directory
        """
        info = os.path.join(directory, '.directory')
        if not os.path.isfile(info):
            return
        f = open(info)
        for l in f.readlines():
            if l.startswith('Icon='):
                self.image = l[5:]
                if self.image.startswith('./'):
                    self.image = self.image[2:]
                self.keys.append('image')
        f.close()


    def parse_bins(self, directory):
        """
        search album.xml (bins)
        """
        binsxml = os.path.join(directory, 'album.xml')
        if not os.path.isfile(binsxml):
            return

        for node in libxml2.parseFile(binsxml).children:
            if not node.name == 'description':
                continue
            for child in node.children:
                if not child.name == 'field':
                    continue
                value = unicode(child.getContent(), 'utf-8').strip()
                key = child.prop('name')
                if key and value:
                    if key == 'sampleimage':
                        image = os.path.join(directory, unicode_to_str(value))
                        if os.path.isfile(image):
                            self.image = image
                            self.keys.append('image')
                    else:
                        self[key] = value
                        if not key in MEDIACORE:
                            # if it's in desc it must be important
                            self.keys.append(key)

# register to kaa.metadata core
register('directory', EXTENSION_DIRECTORY, TYPE_MISC, DirInfo)
