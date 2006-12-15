# -*- coding: iso-8859-1 -*-
# -----------------------------------------------------------------------------
# core.py - basic audio class
# -----------------------------------------------------------------------------
# $Id: core.py 2216 2006-12-10 20:32:21Z dmeyer $
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

from kaa.metadata.core import ParseError, Media, MEDIA_AUDIO, \
     EXTENSION_STREAM
from kaa.metadata.factory import register

# fourcc list
import kaa.metadata.fourcc as fourcc


AUDIOCORE = ['channels', 'samplerate', 'length', 'encoder', 'codec', 'format',
             'samplebits', 'bitrate', 'fourcc', 'trackno' ]

MUSICCORE = ['trackof', 'album', 'genre', 'discs', 'thumbnail' ]


class Audio(Media):
    """
    Audio Tracks in a Multiplexed Container.
    """
    _keys = Media._keys + AUDIOCORE
    media = MEDIA_AUDIO

    def _finalize(self):
        Media._finalize(self)
        if self.codec is not None:
            self.fourcc, self.codec = fourcc.resolve(self.codec)


class Music(Audio):
    """
    Digital Music.
    """
    _keys = Audio._keys + MUSICCORE

    def _finalize(self):
        """
        Correct same data based on specific rules
        """
        Audio._finalize(self)
        if self.trackof:
            try:
                # XXX Why is this needed anyway?
                if int(self.trackno) < 10:
                    self.trackno = u'0%s' % int(self.trackno)
            except (KeyboardInterrupt, SystemExit):
                sys.exit(0)
            except:
                pass
