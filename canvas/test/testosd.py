import sys

import kaa
from kaa.mplayer import MPlayer
from kaa import canvas
# Import test canvas objects
from canvasobjects import MPlayerOSDCanvas, CanvasMovie

# XXX: UPDATE ME: this should point to the mplayer patched with vf_overlay
# and vf_outbuf if it is not already in your default path.
#------------------------------------------------------------
MPlayer.PATH = "/home/tack/projects/mplayer/main/mplayer"
#------------------------------------------------------------


def handle_key(key):
    if key == "q":
        raise SystemExit
    elif key == "a":
        osd.set_color(a = osd.get_color()[3] - 10)
    elif key == "A":
        osd.set_color(a = osd.get_color()[3] + 10)
    elif key == "s":
        osd.show()
    elif key == "h":
        osd.hide()
    elif key == "space":
        mp.pause()
    elif key == "i":
        i = img.as_image()
        i.flip_vertical()
    elif key == "r":
        movie.set_color(a=200)
    elif key == "up":
        mp.seek(60)
    elif key == "down":
        mp.seek(-60)


if len(sys.argv) <= 1:
    print "Usage: %s movie.avi [osdmovie.avi]" % sys.argv[0]
    sys.exit(0)

mp = MPlayer((640, 480))
osd = MPlayerOSDCanvas(mp)

# For testing X11 canvas: uncomment the next 3 lines
#osd = canvas.X11Canvas((640, 480), title = "foobar", use_gl=False)
#osd.add_image("data/background.jpg", size = (640, 480))
### 


if len(sys.argv) > 2:
    mp2 = MPlayer(window = False)
    movie = CanvasMovie(mp2)
    osd.add_child(movie, pos = (50, 50), size=(350,-1))
    mp2.play(sys.argv[2], "-vo null -ao null")
elif isinstance(osd, canvas.X11Canvas):
    movie = CanvasMovie(mp)
    osd.add_child(movie, pos = (50, 50), size=(350,-1))
    # Test clipping
    #movie.clip((10, 10), (200, 100))
    #movie.set_color(a=50)
    

osd.add_font_path("data")
c = osd.add_container(pos=(10,10))
img = c.add_image("data/video.png", color = (255, 255, 255, 255), pos = (420, 300))
c.add_text("Behold my glory!", font = "VeraBD", pos = (30, 15))

# Make the OSD a bit translucent.
osd.set_color(a=200)
# OSD defaults to hidden, so show it.
osd.show()

mp.play(sys.argv[1], "-colorkey 0x010103 -vo xv:ck=set")
# For screenshots :)
#mp.play(sys.argv[1], "-vo x11 -zoom")

print "space: pause | up: seek +60 | down: seek -60 | a: fade out | A: fade in |"
print "i: flip icon | h: hide OSD | s: show OSD | q: quit"
kaa.signals["stdin_key_press_event"].connect(handle_key)

kaa.main()

# Test garbage collection ...
del osd, img, c
if "movie" in globals():
    del movie
import gc
gc.collect()
