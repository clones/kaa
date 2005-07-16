import sys
from kaa import xine, display
import kaa

def key_press(key):
    print "KEY PRESS", key
    if key == 113:
        raise SystemExit

win = display.X11Window(size=(640, 480), title="Movie")
win.show()
x = xine.Xine()
vo = x.open_video_driver("xv", window = win)
ao = x.open_audio_driver()

stream = x.stream_new(ao, vo)
stream.open(sys.argv[1])
stream.play()

kaa.signals["keypress"].connect(key_press)
kaa.main()
