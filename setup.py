import os
import sys
import distutils.core

submodules = [ 'imlib2', 'display', 'mevas', 'thumb', 'epg', 'notifier' ]

for a in sys.argv:
    if a.startswith('--help'):
        distutils.core.setup(name="kaa", version="0.1")
        sys.exit(0)

for m in submodules:
    print '[setup] Entering kaa submodule', m
    os.chdir(m)
    execfile('setup.py')
    os.chdir('..')
    print '[setup] Leaving kaa submodule', m

if sys.argv[1] == 'clean' and len(sys.argv) == 2:
    for m in submodules:
        build = os.path.join(m, 'build')
        if os.path.isdir(build):
            print 'removing %s' % build
            os.system('rm -rf %s' % build)
