# -*- coding: iso-8859-1 -*-
# -----------------------------------------------------------------------------
# mplayer/config.py - config for mplayer backend
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

# python imports
import os
import sys
import gettext

# kaa imports
from kaa.config import Var, Group, Dict, List

# i18 setup for this file
path = os.path.normpath(
    os.path.join(os.path.dirname(__file__), '../../../../share/locale'))
i18n = gettext.translation('kaa.popcorn', path, fallback=True).ugettext

# config variable for mplayer
config = Group(desc=i18n('mplayer configuration'), schema=[
    Var(name='activate', default=True, desc=i18n('activate backend'))
    ])
