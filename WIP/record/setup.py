# python imports
import sys

try:
    # kaa base imports
    from kaa.distribution import Extension, setup
except ImportError:
    print 'kaa.base not installed'
    sys.exit(1)

# NOTE: this is no python module!
# It is a gstreamer plugin not in the gstreamer plugin path.
# When kaa.record2 is init, this module will be added to
# gstreaner on runtime.
tuner = Extension('kaa.record2._gstrecord',
                  [ 'gst/gstdvbtuner.c', 'gst/gsttssplitter.c',
                    'gst/gstmain.c' ],
                  config='gst/config.h')
tuner.config('#define VERSION "0.1"')
tuner.config('#define PACKAGE "kaa.record"')

if not tuner.check_library('gstreamer-0.10', '0.1'):
    print 'gstreamer 0.10 not found'
    sys.exit(1)

setup(module      = 'record2',
      version     = '0.1',
      ext_modules = [ tuner ]
)
