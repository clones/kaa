import sys
sys.path = ['..'] + sys.path

import mmpython

# MAKE SURE /tmp/mmpython exists
#
# you can cache whole directories with
# cachedir dirname
#
# the content of a mounted (!) data cd with
# cachedir cd://device:mountpoint:
# e.g. cachedir cd:///dev/cdrom:/mnt/cdrom:

#mmpython.mediainfo.DEBUG = 0
mmpython.use_cache('cache')

print '%s file(s) are missing in the cache' % mmpython.check_cache(sys.argv[1])

mmpython.cache_dir(sys.argv[1])

