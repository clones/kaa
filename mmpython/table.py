#if 0
# -----------------------------------------------------------------------
# $Id$
# -----------------------------------------------------------------------
# $Log$
# Revision 1.3  2003/06/20 19:57:30  the_krow
# GNU Header
#
#
# -----------------------------------------------------------------------
# MMPython - Media Metadata for Python
# Copyright (C) 2003 Thomas Schueppel
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
# -----------------------------------------------------------------------
#endif

class Table:
	"""
	Table of Metadata. 
	"""
    def __init__(self, hashmap, name):
        self.dict = hashmap
        self.name = name
		self.language = 'en'
        
    def __setitem__(self,key,value):
        self.dict[key] = value
        
    def __getitem__(self,key):
        if self.dict.has_key(key):
            return self.dict[key]
        else:
            return None
         
    def getstr(self,key):
        s = self[key]
        if s and len(s.__str__()) < 100: 
            return s
        else:
            return "Not Displayable"       
         
    def has_key(self, key):
        return self.dict.has_key(key)    
    
    def __str__(self):
        header = "\nTable %s:" % self.name 
        result = reduce( lambda a,b: self[b] and "%s\n        %s: %s" % \
                         (a, b.__str__(), self.getstr(b)) or a, self.dict.keys(), header )
        return result

    def accept(self,mi):
        pass