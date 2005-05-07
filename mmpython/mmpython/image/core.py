# -*- coding: iso-8859-1 -*-
# -----------------------------------------------------------------------------
# core.py - basic image parsing using Imaging
# -----------------------------------------------------------------------------
# $Id$
#
# -----------------------------------------------------------------------------
# MMPython - Media Metadata for Python
# Copyright (C) 2003-2005 Thomas Schueppel, Dirk Meyer
#
# First Edition: Thomas Schueppel <stain@acm.org>
# Maintainer:    Dirk Meyer <dmeyer@tzi.de>
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
import gzip
import logging
from xml.utils import qp_xml

# mmpython imports
import mmpython
from mmpython import mediainfo
import bins

# get logging object
log = logging.getLogger('mmpython')

try:
    import Image as PIL
except:
    log.warning('Python Imaging not found')
    PIL = None


# attributes for image files
ATTRIBUTES = ['description', 'people', 'location', 'event', 'width', 'height',
              'thumbnail','software','hardware', 'dpi']


class ImageInfo(mediainfo.MediaInfo):
    """
    Digital Images, Photos, Pictures.
    """
    def __init__(self):
        MediaInfo.__init__(self)
        for k in ATTRIBUTES:
            setattr(self,k,None)
            self.keys.append(k)

    def parse_external_files(self, filename):
        """
        Parse external files like bins and .comments.
        """
        if os.path.isfile(filename + '.xml'):
            try:
                binsinfo = bins.get_bins_desc(filename)
                # get needed keys from exif infos
                for key in ATTRIBUTES + mediainfo.MEDIACORE:
                    if not self[key] and binsinfo['exif'].has_key(key):
                        self[key] = binsinfo['exif'][key]
                # get _all_ infos from description
                for key in binsinfo['desc']:
                    self[key] = binsinfo['desc'][key]
                    if not key in ATTRIBUTES + mediainfo.MEDIACORE:
                        # if it's in desc it must be important
                        self.keys.append(key)
            except Exception, e:
                log.exception('problem reading the image information')
                pass

        comment_file = os.path.join(os.path.dirname(filename), '.comments',
                                    os.path.basename(filename) + '.xml')
        if os.path.isfile(comment_file):
            try:
                f = gzip.open(comment_file)
                p = qp_xml.Parser()
                tree = p.parse(f)
                f.close()
                for c in tree.children:
                    if c.name == 'Place':
                        self.location = c.textof()
                    if c.name == 'Note':
                        self.description = c.textof()
            except:
                pass


    def add_imaging_information(self, filename):
        """
        Add informations based on imaging (PIL)
        """
        if not PIL:
            return
        try:
            i = PIL.open(filename)
        except:
            raise mediainfo.MMPythonParseError()

        if not self.mime:
            self.mime = 'image/%s' % i.format.lower()

        self.type = i.format_description

        if i.info.has_key('dpi'):
            self['dpi'] = '%sx%s' % i.info['dpi']

        for info in i.info:
            if not info == 'exif':
                log.debug('%s: %s' % (info, i.info[info]))

        self.mode = i.mode
        if not self.height:
            self.width, self.height = i.size
