import kaa.canvas
import kaa.display

canvas = kaa.canvas.FBCanvas((800,600))

background = kaa.canvas.Image("data/background.jpg")
canvas.add_child(background)

hello = kaa.canvas.Text("Hello world!")
hello.move(hcenter = "50%", vcenter = "50%")
canvas.add_child(hello)

kaa.main()

# kaa.display.fb.EvasFramebuffer()
