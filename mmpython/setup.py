#!/usr/bin/env python

"""Setup script for the mmpython distribution."""

__revision__ = "$Id$"

from distutils.core import setup, Extension
import popen2

extensions = [ Extension('mmpython/disc/cdrom', ['disc/cdrommodule.c']) ]

# check for libdvdread (bad hack!)
child = popen2.Popen4('gcc -ldvdread')
if child.fromchild.readline().find('cannot find') == -1:
    # gcc failed, but not with 'cannot find', so libdvd must be
    # somewhere (I hope)
    extensions.append(Extension('mmpython/disc/ifoparser', ['disc/ifomodule.c'],
                                libraries=[ 'dvdread' ], 
                                library_dirs=['/usr/local/lib'],
                                include_dirs=['/usr/local/include']))
child.wait()

setup (# Distribution meta-data
       name = "mmpython",
       version = "0.1",
       description = "Module for retrieving information about media files",
       author = "Thomas Schueppel, Dirk Meyer",
       author_email = "",
       url = "",

       package_dir = {'mmpython.video': 'video',
                      'mmpython.audio': 'audio',
                      'mmpython.audio.eyeD3': 'audio/eyeD3',
                      'mmpython.image': 'image',
                      'mmpython.disc' : 'disc',
                      'mmpython': ''},

       packages = [ 'mmpython', 'mmpython.video', 'mmpython.audio', 'mmpython.audio.eyeD3',
                    'mmpython.image', 'mmpython.disc' ],
       
       # Description of the modules and packages in the distribution
       ext_modules = extensions
                       
      )

