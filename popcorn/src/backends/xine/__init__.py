# -*- coding: iso-8859-1 -*-
# -----------------------------------------------------------------------------
# xine/__init__.py - xine backend
# -----------------------------------------------------------------------------
# $Id$
#
# -----------------------------------------------------------------------------
# kaa.popcorn - Generic Player API
# Copyright (C) 2006 Jason Tackaberry, Dirk Meyer
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

__all__ = [ 'import_backend' ]

# kaa.popcorn imports
from kaa.popcorn.ptypes import *

def get_capabilities():
    """
    Return capabilities of the xine backend.
    """

    # player imports
    from config import config

    capabilities = {
        CAP_OSD : True,
        CAP_CANVAS : True,
        CAP_DYNAMIC_FILTERS : False,
        CAP_VARIABLE_SPEED : True,
        CAP_VISUALIZATION : True,

        CAP_DVD : config.capability.dvd,
        CAP_DVD_MENUS : config.capability.dvdmenu,
        CAP_DEINTERLACE : config.capability.deinterlace
    }

    schemes = [ "file", "fifo", "dvd", "vcd", "cdda", "http", "tcp", "udp",
                "rtp", "smb", "mms", "pnm", "rtsp", "pvr" ]

    # list of extentions when to prefer this player
    exts = ["mpg", "mpeg", "iso"]

    # list of codecs when to prefer this player
    codecs = []

    # list of extentions when to prefer this player
    exts = config.preferred.extentions.split(',')

    # list of codecs when to prefer this player
    codecs = config.preferred.codecs.split(',')

    # list of video driver
    vo = [ 'xv' ]

    return capabilities, schemes, exts, codecs, vo


def import_backend():
    """
    Return player name, class and capability function.
    """
    from player import Xine
    return ("xine", Xine, get_capabilities)
