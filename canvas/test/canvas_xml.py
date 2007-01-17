import sys
import kaa, kaa.canvas
from test_common import *

if len(sys.argv) < 2:
    print 'ERROR: you must specify the canvas xml file as an argument'
    print 'usage: %s <canvas_xml>' % sys.argv[0]
    sys.exit(1)

if output == "DirectFB":
    canvas = kaa.canvas.DirectFBCanvas(size)
elif output == "FB":
    canvas = kaa.canvas.FBCanvas(size)
else: # X11
    canvas = kaa.canvas.X11Canvas(size)

canvas.from_xml(sys.argv[1])
kaa.main()
