import sys
import kaa

from child import GStreamer

player = GStreamer(sys.argv[1])
kaa.main()
