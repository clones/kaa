# -*- coding: iso-8859-1 -*-
# -----------------------------------------------------------------------------
# mmpython.__init__.py
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
# Please see the file freevo/Docs/CREDITS for a complete list of authors.
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

# logging support
import logging
logger = logging.getLogger('mmpython')
if not logger.level:
    # level not set for mmpython, set it to WARNING
    logger.setLevel(logging.WARNING)

# import factory code for mmpython access
from factory import *

# use network functions
USE_NETWORK     = 1
