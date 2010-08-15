# -*- coding: iso-8859-1 -*-
# -----------------------------------------------------------------------------
# ptypes.py - Types and constants used by kaa.popcorn
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

CAP_OSD = 'CAP_OSD'
CAP_CANVAS = 'CAP_CANVAS'
CAP_DYNAMIC_FILTERS = 'CAP_DYNAMIC_FILTERS'
CAP_VARIABLE_SPEED = 'CAP_VARIABLE_SPEED'
CAP_VISUALIZATION = 'CAP_VISUALIZATION'
CAP_DVD = 'CAP_DVD'
CAP_DVD_MENUS = 'CAP_DVD_MENUS'
CAP_DEINTERLACE = 'CAP_DEINTERLACE'

STATE_NOT_RUNNING = 'STATE_NOT_RUNNING'
STATE_IDLE = 'STATE_IDLE'
STATE_OPENING = 'STATE_OPENING'
STATE_OPEN = 'STATE_OPEN'
STATE_PLAYING = 'STATE_PLAYING'
STATE_PAUSED = 'STATE_PAUSED'
STATE_STOPPING = 'STATE_STOPPING'
STATE_SHUTDOWN = 'STATE_SHUTDOWN'

SCALE_KEEP = 'SCALE_KEEP'
SCALE_IGNORE = 'SCALE_IGNORE'
SCALE_4_3 = 'SCALE_4_3'
SCALE_16_9 = 'SCALE_16_9'
SCALE_ZOOM = 'SCALE_ZOOM'

SCALE_METHODS = [ SCALE_KEEP, SCALE_IGNORE, SCALE_4_3, SCALE_16_9, SCALE_ZOOM ]

SEEK_RELATIVE = 'SEEK_RELATIVE'
SEEK_ABSOLUTE = 'SEEK_ABSOLUTE'
SEEK_PERCENTAGE = 'SEEK_PERCENTAGE'

class PlayerError(Exception):
    pass

class PlayerCapError(PlayerError):
    pass
