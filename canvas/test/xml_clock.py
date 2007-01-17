import time, kaa, kaa.canvas
from test_common import *

if output == "DirectFB":
    canvas = kaa.canvas.DirectFBCanvas(size)
elif output == "FB":
    canvas = kaa.canvas.FBCanvas(size)
else: # X11
    canvas = kaa.canvas.X11Canvas(size)

canvas.from_xml("clock.xml")

def update_clock(text):
    text.set_text(time.strftime("%I:%M:%S %p"))

kaa.notifier.Timer(update_clock, canvas.find_object("time")).start(1)

kaa.main()
