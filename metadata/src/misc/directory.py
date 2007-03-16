# -*- coding: iso-8859-1 -*-
# -----------------------------------------------------------------------------
# directory.py - parse directory information
# -----------------------------------------------------------------------------
# $Id$
#
# -----------------------------------------------------------------------------
# kaa-Metadata - Media Metadata for Python
# Copyright (C) 2003-2006 Thomas Schueppel, Dirk Meyer
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

# python imports
import os
import logging
import sys

# kaa imports
from kaa.strutils import unicode_to_str
from kaa import xml

# kaa.metadata imports
import kaa.metadata.core as core
import kaa.metadata.factory as factory

# get logging object
log = logging.getLogger('metadata')


class Directory(core.Media):
    """
    Simple parser for reading a .directory file.
    """
    media = core.MEDIA_DIRECTORY

    def __init__(self, directory):
        core.Media.__init__(self)
        for func in (self.parse_dot_directory, self.parse_bins):
            try:
                func(directory)
            except (KeyboardInterrupt, SystemExit):
                sys.exit(0)
            except:
                log.exception('%s', func)


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
                image = l[5:].strip()
                if not image.startswith('/'):
                    image = os.path.join(directory, image)
                self._set('image', image)
            if l.startswith('Name='):
                self.title = l[5:].strip()
            if l.startswith('Comment='):
                self.comment = l[8:].strip()
        f.close()


    def parse_bins(self, directory):
        """
        search album.xml (bins)
        """
        binsxml = os.path.join(directory, 'album.xml')
        if not os.path.isfile(binsxml):
            return

        doc = xml.Document(binsxml, 'album')
        for child in doc.get_child('description').children:
            key = str(child.getattr('name'))
            if not key or not child.content:
                continue
            if key == 'sampleimage':
                image = os.path.join(directory, unicode_to_str(child.content))
                if not os.path.isfile(image):
                    continue
                self._set('image', image)
                continue
            self._set(key, child.content)

# register to kaa.metadata core
factory.register('directory', core.EXTENSION_DIRECTORY, Directory)
