#!/usr/bin/env python

"""Setup script for the kaa.epg distribution."""

__revision__ = "$Id$"

import os
import distutils.core

# create fake kaa.__init__.py
open('__init__.py', 'w').close()

distutils.core.setup (
    name         = "kaa-epg",
    version      = 0.1,
    description  = "Python EPG module",
    author       = "Freevo Project",
    author_email = "freevo-devel@lists.sourceforge.net",
    url          = "http://freevo.sf.net/kaa",
    
    package_dir  = {"kaa": ".", "kaa.epg": "src" },
    packages     = [ 'kaa.epg' ],
    py_modules   = [ 'kaa.__init__' ],
    )

# delete fake kaa.__init__.py
os.unlink('__init__.py')
