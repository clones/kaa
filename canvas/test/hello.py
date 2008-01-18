import kaa.canvas
from test_common import *

if output == "DirectFB":
    canvas = kaa.canvas.DirectFBCanvas(size)
elif output == "FB":
    canvas = kaa.canvas.FBCanvas(size)
else: # X11
    canvas = kaa.canvas.X11Canvas(size)


background = kaa.canvas.Image("data/background.jpg")
canvas.add_child(background)

hello = kaa.canvas.Text("Hello world!")
hello.move(hcenter = "50%", vcenter = "50%")
canvas.add_child(hello)

kaa.main.run()
