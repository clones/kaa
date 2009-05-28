# -*- coding: iso-8859-1 -*-
# $Id$
# -----------------------------------------------------------------------------
# common.py - Common types and functions shared between core and backends
# -----------------------------------------------------------------------------
# kaa.popcorn - Generic Player API
# Copyright (C) 2008 Jason Tackaberry, Dirk Meyer
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
import kaa

CAP_DYNAMIC_FILTERS = 'CAP_DYNAMIC_FILTERS'
CAP_VARIABLE_SPEED = 'CAP_VARIABLE_SPEED'
CAP_VISUALIZATION = 'CAP_VISUALIZATION'
CAP_DVD = 'CAP_DVD'
CAP_DVD_MENUS = 'CAP_DVD_MENUS'
CAP_DEINTERLACE = 'CAP_DEINTERLACE'
CAP_VIDEO = 'CAP_VIDEO'
CAP_VO_SHM = 'CAP_VO_SHM'

STATE_NOT_RUNNING = 'STATE_NOT_RUNNING'
STATE_IDLE = 'STATE_IDLE'
STATE_OPENING = 'STATE_OPENING'
STATE_OPEN = 'STATE_OPEN'
STATE_PLAYING = 'STATE_PLAYING'
STATE_PAUSED = 'STATE_PAUSED'
STATE_STOPPING = 'STATE_STOPPING'

# States in which the backend is available.
STATES_ACTIVE = (STATE_OPENING, STATE_IDLE, STATE_OPEN, STATE_PLAYING, STATE_PAUSED)

SCALE_KEEP = 'SCALE_KEEP'
SCALE_IGNORE = 'SCALE_IGNORE'
SCALE_4_3 = 'SCALE_4_3'
SCALE_16_9 = 'SCALE_16_9'
SCALE_ZOOM = 'SCALE_ZOOM'
SCALE_METHODS = (SCALE_KEEP, SCALE_IGNORE, SCALE_4_3, SCALE_16_9, SCALE_ZOOM)

SEEK_RELATIVE = 'SEEK_RELATIVE'
SEEK_ABSOLUTE = 'SEEK_ABSOLUTE'
SEEK_PERCENTAGE = 'SEEK_PERCENTAGE'

class PlayerError(Exception):
    pass


class PlayerAbortedError(PlayerError, kaa.InProgressAborted):
    pass


def precondition(states=(), notstates=(), backend=None):
    """
    Decorator that enforces certain preconditions.  If any precondition fails
    upon invocation of the decorated function, an exception is raised. 
    
    @param states: a tuple of STATE_* values; the current state must be one
        of the supplied states.
    @param notstates: a tuple of STATE_* values; the current state must NOT be
        one of the supplied states.
    @param backend: if True, requires the proxy have a backend.  (This of
        course is only useful when decorating a proxy method and isn't useful
        directly to a backend.)
    """
    # Coerce arguments to sequences.
    states = states if isinstance(states, (tuple, list, set)) else (states,)
    notstates = notstates if isinstance(notstates, (tuple, list, set)) else (notstates,)

    def decorator(func):
        from kaa.utils import wraps
        @wraps(func)
        def newfunc(self, *args, **kwargs):
            if states and self.state not in states:
                raise PlayerError('current state %s is not in one of required: %s' % \
                                  (self.state, ', '.join(states)))
            if notstates and self.state in notstates:
                raise PlayerError('current state %s must not be one of: %s' % \
                                  (self.state, ', '.join(notstates)))

            if backend and not getattr(self, '_backend', None):
                raise PlayerError('not callable until after open()')

            return func(self, *args, **kwargs)
        
        return newfunc

    return decorator
