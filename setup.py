import os
import sys
import distutils.core

for a in sys.argv:
    if a.startswith('--help'):
        distutils.core.setup(name="kaa", version="0.1")
        sys.exit(0)

for submodule in [ 'imlib2', 'thumb', 'epg' ]:
    print '[setup] Entering kaa submodule', submodule
    os.chdir(submodule)
    execfile('setup.py')
    os.chdir('..')
    print '[setup] Leaving kaa submodule', submodule
