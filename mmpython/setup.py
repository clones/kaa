#!/usr/bin/env python

"""Setup script for the mmpython distribution."""

__revision__ = "$Id$"

from distutils.core import setup, Extension

setup (# Distribution meta-data
       name = "mmpython",
       version = "0.1",
       description = "Module for retrieving information about media files",
       author = "Thomas Schueppel, Dirk Meyer",
       author_email = "",
       url = "",

       package_dir = {'mmpython.video': 'video',
                      'mmpython.audio': 'audio',
                      'mmpython.image': 'image',
                      'mmpython.disc' : 'disc',
                      'mmpython': ''},

       packages = [ 'mmpython', 'mmpython.video', 'mmpython.audio', 'mmpython.image',
                    'mmpython.disc' ],
       
       # Description of the modules and packages in the distribution
       ext_modules = [ Extension('mmpython/disc/ifoparser', ['disc/ifomodule.c'],
                                 libraries=[ 'dvdread' ]),
                       Extension('mmpython/disc/cdrom', ['disc/cdrommodule.c']) ]
      )
