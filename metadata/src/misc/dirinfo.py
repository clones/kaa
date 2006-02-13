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

# kaa imports
from kaa.base.strutils import unicode_to_str
from kaa.base import libxml2
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
        try:
            self.parse_dot_directory(directory)
        except:
            log.exception('parse_dot_directory')
        try:
            self.parse_bins(directory)
        except:
            log.exception('parse_bins')


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

        xml = libxml2.Document(binsxml, 'album')
        for child in xml.get_child('description').children:
            key = str(child.getattr('name'))
            if not key or not child.content:
                continue
            if key == 'sampleimage':
                image = os.path.join(directory, unicode_to_str(child.content))
                if not os.path.isfile(image):
                    continue
                self.image = image
                self.keys.append('image')
                continue
            self[key] = child.content
            if not key in MEDIACORE:
                # if it's in desc it must be important
                self.keys.append(key)

# register to kaa.metadata core
register('directory', EXTENSION_DIRECTORY, TYPE_MISC, DirInfo)
