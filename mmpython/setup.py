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
                      'mmpython': ''},

       packages = [ 'mmpython', 'mmpython.video', 'mmpython.audio', 'mmpython.image' ],
       
       # Description of the modules and packages in the distribution
       ext_modules = [ Extension('mmpython/video/ifoinfo', ['video/ifomodule.c'],
                                 libraries=[ 'dvdread' ]) ]
      )
