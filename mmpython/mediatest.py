#!/usr/bin/python

import sys
sys.path.append('..')

import mmpython

USE_CACHE = 1

if USE_CACHE:
    mmpython.use_cache('/tmp/')

medium = mmpython.parse(sys.argv[1])

#medium.expand_keywords()
if medium:
    print "medium is: %s" % medium.type
    print medium
else:
    print "No Match found"


if USE_CACHE:
    mmpython.cache_disc(medium)
    
