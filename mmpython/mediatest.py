#!/usr/bin/python

import mediainfo
import audio.ogginfo
import audio.pcminfo
import audio.mp3info
import video.riffinfo
import video.mpeginfo
import video.asfinfo
import video.movinfo
import image.jpginfo
import image.pnginfo
import image.tiffinfo

import disc.dvdinfo
import disc.vcdinfo

import sys

m = mediainfo.get_singleton()
medium = m.create_from_filename(sys.argv[1])
#medium.expand_keywords()
if medium:
    print "medium is: %s" % medium.type
    for k in medium.keys:
        val = medium[k]
        if val != None: 
            print "  %s: %s" % (k,val)
    try:
        for v in medium.video:
            for k in v.keys:
                val = v[k]
                if val != None: 
                    print "  Video: %s: %s" % (k,val)
    except: 
        pass
    try:
        for v in medium.audio:
            for k in v.keys:
               val = v[k]
               if val != None: 
                   print "  Audio: %s: %s" % (k,val)
    except: 
        pass
else:
    print "No Match found"

