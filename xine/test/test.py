import sys
from kaa import xine, display
import kaa, gc

def key_press(key):
    print "KEY PRESS", key
    if key == 113:
        raise SystemExit

#win = display.X11Window(size=(640, 480), title="Movie")
#win.show()
x = xine.Xine()
vo_none = x.open_video_driver("none")
#vo = x.open_video_driver("xv", window = win)
ao = x.open_audio_driver()

post = x.post_init("buffer", video_targets = [vo_none])
a = post.get_video_inputs()
#stream = x.stream_new(ao, a[0])
#stream.open(sys.argv[1])
#stream.play()
print x.list_post_plugins()
print post.get_parameters_desc()
print post.get_parameters()
print post.set_parameter("ptr", 42)
print post.get_parameters()

kaa.signals["keypress"].connect(key_press)
kaa.main()
