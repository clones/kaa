#if 0
# -----------------------------------------------------------------------
# $Id$
# -----------------------------------------------------------------------
# $Log$
# Revision 1.7  2003/07/02 09:16:42  the_krow
# bugfix if no language file was found
#
# Revision 1.6  2003/07/02 09:09:41  the_krow
# i18n stuff added to AVI
# some debug outputs removed
#
# Revision 1.5  2003/06/23 09:22:54  the_krow
# Typo and Indentation fixes.
#
# Revision 1.4  2003/06/23 09:20:29  the_krow
# Added Language to table Attributes
#
# Revision 1.3  2003/06/20 19:57:30  the_krow
# GNU Header
#
#
# -----------------------------------------------------------------------
# MMPython - Media Metadata for Python
# Copyright (C) 2003 Thomas Schueppel, Dirk Meyer
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

from gettext import GNUTranslations
import os

LOCALEDIR = 'i18n'

class Table:
    def __init__(self, hashmap, name):
        self.dict = hashmap
        self.name = name
        self.language = 'en'
        self.translations = {}
        self.languages = []
        self.i18ndir = os.path.join(LOCALEDIR, name.lower())
        try:
            self.read_translations()
        except:
            pass
    
    def read_translations(self):
        for filename in [x for x in os.listdir(self.i18ndir) if x.endswith('.mo')]:
            lang = filename[:-3]
            filename = os.path.join(self.i18ndir, filename)
            f = open(filename, 'rb')
            self.translations[lang] = GNUTranslations(f)
            f.close()
        self.languages = self.translations.keys()
        
    def gettext(self, message, language = None):
        try:
            return self.translations[language].gettext(message)
        except KeyError:
            return "%s (No Message in '%s')" % (message, language)
        
    def __setitem__(self,key,value):
        self.dict[key] = value
        
    def __getitem__(self,key):
        try:
            return self.dict[key]
        except KeyError:
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
                         (a, self.gettext(b.__str__(),'en'), self.getstr(b)) or a, self.dict.keys(), header )
        return result

    def accept(self,mi):
        pass