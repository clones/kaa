# -*- coding: iso-8859-1 -*-
# -----------------------------------------------------------------------------
# setup.py - Setup script for kaa
# -----------------------------------------------------------------------------
# $Id$
#
# -----------------------------------------------------------------------------
# kaa - Kaa Media Repository
# Copyright (C) 2005 Dirk Meyer, Jason Tackaberry
#
# First Edition: Dirk Meyer <dmeyer@tzi.de>
# Maintainer:    Dirk Meyer <dmeyer@tzi.de>
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

import os
import sys
import distutils.core

submodules = [ 'base', 'imlib2', 'display', 'mevas', 'thumb', 'epg', 'record',
               'metadata', 'evas', 'canvas', 'xine', 'player', 'webinfo' ]

for a in sys.argv:
    if a.startswith('--help'):
        distutils.core.setup(name="kaa", version="0.1")
        sys.exit(0)

if sys.argv[1] == 'clean' and len(sys.argv) == 2:
    for m in submodules:
        build = os.path.join(m, 'build')
        if os.path.isdir(build):
            print 'removing %s' % build
            os.system('rm -rf %s' % build)
        version = os.path.join(m, 'src/version.py')
        if os.path.isfile(version):
            print 'removing %s' % version
            os.unlink(version)
            
else:
    failed = []
    build = []
    for m in submodules:
        print '[setup] Entering kaa submodule', m
        os.chdir(m)
        try:
            execfile('setup.py')
        except SystemExit:
            print 'failed to build', m
            failed.append(m)
            if m == 'base':
                sys.exit(1)
        else:
            build.append(m)
        os.chdir('..')
        print '[setup] Leaving kaa submodule', m

        if m == 'base':
            # Adding base/build/lib to the python path so that all kaa modules
            # can find the distribution file of kaa.base
            for subdir in os.listdir('base/build'):
                if not subdir.startswith('lib'):
                    continue
                sys.path.insert(0, '../base/build/%s' % subdir)

    print
    print 'Summary:'
    print '+', ', '.join(build)
    print '-', ', '.join(failed)
    print
    print 'The failed modules (-) may not be required by Freevo, e.g.'
    print 'evas, canvas and xine are not needed right now.'
