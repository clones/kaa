import kaa.canvas
import kaa.display

canvas = kaa.canvas.DirectFBCanvas((800,600))
canvas.add_font_path("./data/")

background = kaa.canvas.Image("data/background.jpg")
canvas.add_child(background)

hello = kaa.canvas.Text("H")
# video = kaa.canvas.Movie("data/video.png")
# hello.set_font("VeraBd")
hello.move(hcenter = "50%", vcenter = "50%")
canvas.add_child(hello)
# canvas.add_child(video)

kaa.main()

# We're getting a segfault here.  run "gdb python", then r, then import dfbtest, then bt.
# #0  0xb7e3d060 in free () from /lib/tls/libc.so.6
# #1  0xb7e3ec4f in malloc () from /lib/tls/libc.so.6
# #2  0xb784e383 in __imlib_ProduceImage () at image.c:145
# #3  0xb784f2fb in __imlib_CreateImage (w=976, h=976, data=0x3d0) at image.c:952
# #4  0xb784797d in imlib_render_str (im=0x829f3d8, fn=0x829aee8, drx=0, dry=0, text=0xb73b77b4 "H ", r=255 '?', g=255 '?', 
#     b=255 '?', a=255 '?', dir=0 '\0', angle=0, retw=0xbf943e44, reth=0xbf943e48, blur=0, nextx=0xbf943e4c, nexty=0xbf943e50, 
#     op=OP_COPY, clx=0, cly=0, clw=0, clh=0) at font_draw.c:89
#5  0xb7836781 in imlib_text_draw_with_return_metrics (x=0, y=0, text=0xb73b77b4 "H ", width_return=0x0, height_return=0x0, 
#     horizontal_advance_return=0x0, vertical_advance_return=0x0) at api.c:3131
#6  0xb78c90b4 in Image_PyObject__draw_text (self=0x0, args=0x0) at src/image.c:430
#7  0x080b9485 in PyEval_EvalFrame ()
#
# In this test the background is 800x600, so what's up with the w=976, h=976 up there??
