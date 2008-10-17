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

submodules = [ 'base', 'imlib2', 'display', 'mevas', 'epg',
               'metadata', 'xine', 'cherrypy', 'beacon', 'popcorn',
               'feedmanager' ]

# We require python 2.4 or later, so complain if that isn't satisfied.
if sys.version.split()[0] < '2.4':
    print "Python 2.4 or later required."
    sys.exit(1)

for a in sys.argv:
    if a.startswith('--help'):
        distutils.core.setup(name="kaa", version="0.1")
        sys.exit(0)

# if no arguments, or --help* requested, return errormessage from core
if len(sys.argv) == 1:
    distutils.core.setup(name="kaa", version="0.1")
    sys.exit(0)

if len(sys.argv) == 2 and sys.argv[1] == 'clean':
    for m in submodules:
        for file in ('build', 'dist', 'src/version.py', 'MANIFEST'):
            if m == 'base' and file == 'src/version.py':
                continue
            file = os.path.join(m, file)
            if os.path.isdir(file):
                print 'removing %s' % file
                os.system('rm -rf %s' % file)
            if os.path.isfile(file):
                print 'removing %s' % file
                os.unlink(file)
            
elif len(sys.argv) == 2 and sys.argv[1] == 'doc':
    if not os.path.isdir('doc/html'):
        os.makedirs('doc/html')
    for m in submodules:
        if os.path.isfile('%s/doc/Makefile' % m):
            print '[setup] Entering kaa submodule', m
            os.chdir(m)
            try:
                # execfile('setup.py')
                pass
            except SystemExit:
                print 'failed to create doc for', m
            os.chdir('..')
            if not os.path.exists('doc/html/%s' % m):
                os.symlink('../../%s/doc/html' % m, 'doc/html/%s' % m)
            print '[setup] Leaving kaa submodule', m
    os.chdir('doc')
    os.system('make html')
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
