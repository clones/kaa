#!/usr/bin/python

import sys
sys.path.append('..')

import mmpython

USE_CACHE = 1

if USE_CACHE:
    mmpython.use_cache('/tmp/')

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
    
