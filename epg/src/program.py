# -*- coding: iso-8859-1 -*-
# -----------------------------------------------------------------------------
# program.py - program class
# -----------------------------------------------------------------------------
# $Id$
# -----------------------------------------------------------------------------
# kaa.epg - EPG Database
# Copyright (C) 2004-2005 Jason Tackaberry, Dirk Meyer, Rob Shortt
#
# First Edition: Jason Tackaberry <tack@sault.org>
# Maintainer:    Dirk Meyer <dischi@freevo.org>
#                Rob Shortt <rob@tvcentric.com>
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
## You should have received a copy of the GNU General Public License along
# with this program; if not, write to the Free Software Foundation, Inc.,
# 59 Temple Place, Suite 330, Boston, MA 02111-1307 USA
#
# -----------------------------------------------------------------------------

class Program(object):
    """
    kaa.epg program class.
    """
    def __init__(self, channel, dbdata):
        self.channel = channel
        self._dbdata = dbdata

        self.start = dbdata.get('start', 0)
        self.stop = dbdata.get('stop', 0)
        self.title = dbdata.get('title', u'')
        self.description = dbdata.get('desc', u'')
        self.subtitle = dbdata.get('subtitle',  u'')
        self.episode = dbdata.get('episode', u'')
        self.genre = dbdata.get('genre', u'')
