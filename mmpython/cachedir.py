import sys
sys.path.append('..')

import mmpython

mmpython.mediainfo.DEBUG = 0
mmpython.use_cache('/tmp/')

print '%s file(s) are missing in the cache' % mmpython.check_cache(sys.argv[1])

mmpython.cache_dir(sys.argv[1])

