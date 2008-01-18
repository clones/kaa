import kaa, kaa.canvas
from test_common import *

if output == "DirectFB":
    canvas = kaa.canvas.DirectFBCanvas(size)
elif output == "FB":
    canvas = kaa.canvas.FBCanvas(size)
else: # X11
    canvas = kaa.canvas.X11Canvas(size)

canvas.add_child(kaa.canvas.Image("data/background.jpg"))

container = canvas.add_child(kaa.canvas.Container(), hcenter = "50%", vcenter = "50%")

frame = kaa.canvas.Image("data/frame.png")
frame.set_border(30, 30, 30, 30)
container.add_child(frame, width = "75%", height = "50%")

text = kaa.canvas.Text("Text inside a container.")
container.add_child(text, hcenter = "50%", vcenter = "50%")

kaa.main.run()
