import sys

import mediainfo
import cache

import audio.ogginfo
import audio.pcminfo
import video.riffinfo
import video.mpeginfo
import video.asfinfo
import video.movinfo
import video.vcdinfo
import image.jpginfo
import image.pnginfo
import image.tiffinfo

import disc.dvdinfo
import disc.vcdinfo
import disc.audioinfo
import audio.mp3info
#import audio.eyed3info


object_cache    = None
uncachable_keys = [ 'thumbnail', ]


def use_cache(directory):
    """
    use directory to search for cached results
    """
    global object_cache
    object_cache = cache.Cache(directory)


def check_cache(directory):
    """
    Return how many files in this directory are not in the cache. It's
    possible to guess how much time the update will need.
    """
    global object_cache
    if not object_cache:
        return -1
    return object_cache.check_cache(directory)


def cache_dir(directory, uncachable_keys = uncachable_keys):
    """
    cache every file in the directory for future use
    """
    global object_cache
    if not object_cache:
        return {}
    return object_cache.cache_dir(directory, uncachable_keys)


def cache_disc(info):
    """
    cache disc informations for future use
    """
    return object_cache.cache_disc(info)


def parse(filename, bypass_cache = 0):
    """
    parse the file
    """
    global object_cache

    if object_cache and not bypass_cache:
        try:
            return object_cache.find(filename)
        except cache.FileNotFoundException:
            pass
        
    return mediainfo.get_singleton().create_from_filename(filename)
