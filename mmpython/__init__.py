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


def parse(filename):
    return mediainfo.get_singleton().create_from_filename(filename)
