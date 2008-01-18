import kaa, kaa.canvas
from test_common import *

if output == "DirectFB":
    canvas = kaa.canvas.DirectFBCanvas(size)
elif output == "FB":
    canvas = kaa.canvas.FBCanvas(size)
else: # X11
    canvas = kaa.canvas.X11Canvas(size)

box = canvas.add_child(kaa.canvas.HBox())
box.add_child(kaa.canvas.Rectangle(), width="30%", height="100%", color = "#ff0000")
box.add_child(kaa.canvas.Rectangle(), width="70%", height="100%", color = "#0000ff")

kaa.main.run()
