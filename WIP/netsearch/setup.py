# python imports
import sys

try:
    # kaa base imports
    from kaa.distribution import Extension, setup
except ImportError:
    print 'kaa.base not installed'
    sys.exit(1)

ext_modules = []

ofa = Extension('kaa.netsearch.ofa', [ 'src/ofa.cc' ])
if not ofa.check_library('libofa', '0.9'):
    print 'libofa >= 0.9 not found'
    print 'building without musicdns support'
else:
    ext_modules.append(ofa)

setup(module      = 'netsearch',
      version     = '0.1',
      ext_modules = ext_modules
)
