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
import disc.audioinfo

import sys

m = mediainfo.get_singleton()
medium = m.create_from_filename(sys.argv[1])
#medium.expand_keywords()
if medium:
    print "medium is: %s" % medium.type
    print medium
else:
    print "No Match found"

