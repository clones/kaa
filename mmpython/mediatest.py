#!/usr/bin/python

import sys
sys.path.append('..')

import mmpython

# Usage:
# mediatest files

# files can be a normal file, a device for VCD/VCD/AudioCD or a cd-url
# cd://device:mountpoint:file, e.g. for bla.avi:
# cd:///dev/cdrom:/mnt/cdrom:bla.avi

# To use the cache, make sure /tmp/mmpython exists
# DVD/VCD/AudioCDs are cached with this proram when USE_CACHE == 1

USE_CACHE = 1

if USE_CACHE:
    mmpython.use_cache('/tmp/mmpython')

for file in sys.argv[1:]:
    medium = mmpython.parse(file)
    print "filename : %s" % file

    if medium:
        print "medium is: %s" % medium.type
        print medium
        print
        print
    else:
        print "No Match found"


    if USE_CACHE:
        mmpython.cache_disc(medium)
    
