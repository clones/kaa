#!/usr/bin/python

import sys
sys.path.append('..')

import mmpython

medium = mmpython.parse(sys.argv[1])
#medium.expand_keywords()
if medium:
    print "medium is: %s" % medium.type
    print medium
else:
    print "No Match found"

