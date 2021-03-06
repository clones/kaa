# -*- coding: iso-8859-1 -*-
# $Id$
# -----------------------------------------------------------------------------
# manager - manage the loaded backends
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
# -----------------------------------------------------------------------------

__all__ = [ 'get_player_class', 'get_all_players' ]

# python imports
import os
import logging

# kaa imports
import kaa.metadata

# kaa.popcorn imports
from ..common import *
from ..config import config

# internal list of players
_players = {}
_backends_imported = False

# get logging object
log = logging.getLogger('popcorn.manager')

def import_backends():
    global _backends_imported
    if _backends_imported:
        return

    for backend in config:
        if getattr(getattr(config, backend), 'enabled', False):
            try:
                # import the backend and register it.
                exec('from %s import import_backend' % backend)
                player_id, cls, get_caps_callback = import_backend()
            except ImportError, e:
                continue
            if player_id in _players:
                return log.warning("Player '%s' already registered", player_id)

            # set player id (which is probably the same as the backend 
            # dir name, but it's up to the backend).
            cls._player_id = player_id

            # FIXME: we just defer calling get_caps_callback until the first time
            # a player is needed, but we should do this in a thread when the system
            # is idle.
            _players[player_id] = {
                'class': cls,
                'callback': get_caps_callback,
                'loaded': False
            }
            
    # This function only ever needs to be called once.
    _backends_imported = True


def get_player_class(media, caps=None, exclude=None, force=None, cfg=None):
    """
    Searches the registered players for the most capable player given the mrl
    or required capabilities.  A specific player can be returned by specifying
    the player id.  If exclude is specified, it is a name (or list of names)
    of players to skip (in case one or more players are known not to work with
    the given mrl).  The player's class object is returned if a suitable
    player is found, otherwise None.
    """
    import_backends()

    if cfg is None:
        # No user-overridden config specified, use global default.
        cfg = config

    # Ensure all players have their capabilities fetched.
    for player_id in _players.keys()[:]:
        if _players[player_id]['loaded']:
            continue

        player_caps, schemes, exts, codecs, vo = _players[player_id]['callback']()

        if player_caps is None:
            # failed to load, ignore this player
            log.error('Failed to load backend: %s', player_id)
            del _players[player_id]
            continue
            
        _players[player_id].update({
            'caps': player_caps,
            'schemes': schemes,
            # Prefer this player for these extensions.
            'extensions': exts,
            # Prefer this player for these codecs.
            'codecs': codecs,
            # Supported video driver
            'vdriver': vo,
            'loaded': True,
        })

        cls = _players[player_id]['class']
        # Note: cls._player_caps are without the rating!
        cls._player_caps = [ k for k, v in player_caps.items() if k and v ]

    if force != None and force in _players:
        player = _players[force]
        if media.scheme not in player['schemes']:
            return None
        # return forced player, no matter if the other
        # capabilities match or not
        return player['class']

    ext = os.path.splitext(media.url)[1]
    if ext:
        ext = ext.lstrip('.')

    if caps != None and type(caps) not in (tuple, list):
        caps = (caps,)
    if exclude != None and type(exclude) not in (tuple, list):
        exclude  = (exclude,)

    codecs = []
    if media.media == kaa.metadata.MEDIA_AV:
        codecs.extend( [ x.fourcc for x in media.video if x.fourcc ] )
        codecs.extend( [ x.fourcc for x in media.audio if x.fourcc ] )
    if 'fourcc' in media and media.fourcc:
        codecs.append(media.fourcc)

    choice = None

    for player_id, player in _players.items():
        if media.scheme not in player["schemes"]:
            # scheme is not supported by this player.
            log.debug('skip %s, does not support %s', player_id, media.scheme)
            continue
        
        if exclude and player_id in exclude:
            # Player is in exclude list.
            log.debug('skip %s, in exclude list', player_id)
            continue

        rating = 0
        if caps:
            # Rate player on the given capabilities. If one or more needed
            # capabilities are False or 0, skip this player
            for c in caps:
                r = player['caps'].get(c, None)
                if not r:
                    log.debug('Backend %s lacks required capability %s, skipping', player_id, c)
                    rating = -1
                    break
                else:
                    # Capability value is either True or a numeric ranking.
                    rating += int(r)

            if rating == -1:
                # Player missing required cap, skip to next player.
                continue

        if ext and ext in player['extensions']:
            # config indicates backend should be preferred for this extension.
            rating += 10

        for c in codecs:
            if c in player['codecs']:
                # config indicates backend should be preferred for this codec
                rating += 10
            
        if cfg.preferred == player_id:
            # Bump up the rating if this is specified as the prefered player,
            # to bias our selection in favor of this one.
            rating += 5

        log.debug('%s rating: %s', player_id, rating)
        if not choice or choice[1] < rating:
            choice = player, rating

    if not choice:
        return None

    return choice[0]['class']


def get_all_players():
    """
    Return all player id strings.
    """
    import_backends()
    return _players.keys()
