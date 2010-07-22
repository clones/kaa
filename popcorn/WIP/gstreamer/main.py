import sys
import os

# insert kaa path information
__site__ = os.path.normpath(os.path.join(os.path.dirname(__file__), '../../../..'))
if not __site__ in sys.path:
    sys.path.insert(0, __site__)

import kaa

from child import GStreamer

player = GStreamer()
kaa.main.run()
