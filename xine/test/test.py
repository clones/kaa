import sys
from kaa import xine, display
import kaa, gc

def key_press(key):
    print "KEY PRESS", key
    if key == 113:
        raise SystemExit

win = display.X11Window(size=(640, 480), title="Movie")
win.set_cursor_hide_timeout(0)
win.show()
x = xine.Xine()
vo_none = x.open_video_driver("none")
vo = x.open_video_driver("xv", window = win)
ao = x.open_audio_driver()

post = x.post_init("buffer", video_targets = [vo])
print post.list_inputs()
print post.list_outputs()
a = post.get_video_inputs()

print post.get_input("video")

#apost = x.post_init("stretch", audio_targets = [ao])
#apost.set_parameter("factor", 0.3)
#print apost.get_parameters()

stream = x.stream_new(ao, vo)
source = stream.get_video_source()
#stream = x.stream_new(apost.get_audio_inputs()[0], a[0])
stream.open(sys.argv[1])
print "Start playing"
stream.play(time = 60*10)
print "Playing"
print x.list_post_plugins()
#print post.get_parameters()
print post.set_parameters(ptr = 42)
#print post.set_parameters(gamma = 1.5, contrast = 10.5)
#print post.get_parameters()

print "connect"
kaa.signals["keypress"].connect(key_press)
print "START MAIN"
kaa.main()
