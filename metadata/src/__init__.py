# -*- coding: iso-8859-1 -*-
# -----------------------------------------------------------------------------
# kaa.metadata.__init__.py
# -----------------------------------------------------------------------------
# $Id$
#
# -----------------------------------------------------------------------------
# kaa-Metadata - Media Metadata for Python
# Copyright (C) 2003-2006 Thomas Schueppel, Dirk Meyer
#
# First Edition: Thomas Schueppel <stain@acm.org>
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

try:
    # check deps
    import libxml2
except ImportError:
    print 'libxml2 python bindings not installed'
    raise ImportError('libxml2 python bindings not installed')

# import factory code for kaa.metadata access
from factory import *
from disc.discinfo import cdrom_disc_id as getid
from mediainfo import MediaInfo, MEDIA_AUDIO, MEDIA_VIDEO, MEDIA_IMAGE, \
     MEDIA_AV, MEDIA_SUBTITLE, MEDIA_CONTAINER, MEDIA_DIRECTORY


# use network functions
USE_NETWORK     = 1
