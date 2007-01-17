import kaa, kaa.canvas
from test_common import *

if output == "DirectFB":
    canvas = kaa.canvas.DirectFBCanvas(size)
elif output == "FB":
    canvas = kaa.canvas.FBCanvas(size)
else: # X11
    canvas = kaa.canvas.X11Canvas(size)

canvas.add_child(kaa.canvas.Image("data/background.jpg"))

c = canvas.add_container(width=100, height=100, hcenter="50%", top=30)
c.add_child(kaa.canvas.Rectangle(), width=200, height=200, color="#44ffff55")
c.add_child(kaa.canvas.Text("Text and rect will overflow"), clip = None)

c = canvas.add_container(width=100, height=100,  clip="auto", hcenter="50%", top=300)
c.add_child(kaa.canvas.Rectangle(), width=200, height=200, color="#ff44ff55")
c.add_child(kaa.canvas.Text("Text is clipped"))

kaa.main()
