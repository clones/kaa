import sys
sys.path.append('..')

import mmpython

mmpython.mediainfo.DEBUG = 0
mmpython.use_cache('/tmp/')
mmpython.cache_dir(sys.argv[1])

