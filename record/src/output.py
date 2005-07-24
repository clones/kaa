# -*- coding: iso-8859-1 -*-
# -----------------------------------------------------------------------------
# output.py - Output plugins
# -----------------------------------------------------------------------------
# $Id$
#
# -----------------------------------------------------------------------------
# kaa-record - A recording module
# Copyright (C) 2005 Sönke Schwardt, Dirk Meyer
#
# First Edition: Dirk Meyer <dmeyer@tzi.de>
# Maintainer:    Dirk Meyer <dmeyer@tzi.de>
#
# Please see the file doc/CREDITS for a complete list of authors.
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

# kaa.record imports
import _op

class Filewriter(object):
    """
    A file writer ouput plugin.
    """
    
    FT_RAW  = 0
    FT_MPEG = 1

    def __init__(self, filename, chunksize, type):
        self.filename = filename
        self.chunksize = chunksize
        if not type in (self.FT_RAW, self.FT_MPEG):
            raise AttributeError('Invalid type')
        self.type = type
        
    def _create_plugin(self):
        """
        Create the C++ OutputPlugin object. Do not use this function in
        your python code or you will create a memory leak.
        """
        return _op.Filewriter(self.filename, self.chunksize, self.type)
