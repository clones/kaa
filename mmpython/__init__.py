import sys
import os

import mediainfo
try:
    import cache
except ImportError:
    pass

import audio.ogginfo
import audio.pcminfo
import video.riffinfo
import video.mpeginfo
import video.asfinfo
import video.movinfo
import image.jpginfo
import image.pnginfo
import image.tiffinfo
import video.vcdinfo
import video.realinfo
import video.ogminfo
try:
    import disc.discinfo
    import disc.dvdinfo
    import disc.vcdinfo
    import disc.audioinfo
    import disc.datainfo
except ImportError:
    pass
import audio.mp3info
#import audio.eyed3info


object_cache    = None
uncachable_keys = [ 'thumbnail', ]


def use_cache(directory):
    """
    use directory to search for cached results
    """
    global object_cache
    if not os.path.isdir(directory):
        print 'WARNING: cache directory %s doesn\'t exists, caching deactivated' % directory
        return 0
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
    info = mediainfo.get_singleton().create_from_filename(filename)
    if info and object_cache and isinstance(info, disc.discinfo.DiscInfo):
        object_cache.cache_disc(info)
    return info

