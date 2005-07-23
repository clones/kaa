import sys
from kaa import xine, display, notifier
import kaa, gc, weakref

def key_press(key, stream):
    global post
    print "KEY PRESS", key

    ch = stream.get_parameter(xine.PARAM_AUDIO_CHANNEL_LOGICAL)
    lang = stream.get_audio_lang(ch)
    print "Channel language", lang
    if key == "q":
        raise SystemExit
    elif key == "space":
        speed = stream.get_parameter(xine.PARAM_SPEED)
        if speed == xine.SPEED_PAUSE:
            stream.set_parameter(xine.PARAM_SPEED, xine.SPEED_NORMAL)
        else:
            stream.set_parameter(xine.PARAM_SPEED, xine.SPEED_PAUSE)
    elif key == "a":
        post.unwire()
        xine._debug_show_chain(stream._stream)

    elif key == "up":
        if lang == "menu":
            stream.send_event(xine.EVENT_INPUT_UP)
        else:
            stream.seek_relative(60)
    elif key == "down":
        if lang == "menu":
            stream.send_event(xine.EVENT_INPUT_DOWN)
        else:
            stream.seek_relative(-60)

    elif key == "m":
        print "Send menu 2"
        stream.send_event(xine.EVENT_INPUT_MENU2)

    elif key == "enter":
        stream.send_event(xine.EVENT_INPUT_SELECT)

    print "End handle event"

win = display.X11Window(size=(640, 480), title="Movie")
win.set_cursor_hide_timeout(0)
x = xine.Xine()
print x.get_log_names()
vo_none = x.open_video_driver("none")
vo = x.open_video_driver("xv", window = win)
ao = x.open_audio_driver()
stream = x.new_stream(ao, vo)
def show_event(event):
    print "EVENT SIGNAL", event.type, event.data
    stream = event.get_stream()
    print "Stream width", stream.get_parameter(xine.STREAM_INFO_VIDEO_WIDTH)
    print "Stream height", stream.get_parameter(xine.STREAM_INFO_VIDEO_HEIGHT)
    if event.type == xine.EVENT_UI_CHANNELS_CHANGED:
        ch = stream.get_parameter(xine.PARAM_AUDIO_CHANNEL_LOGICAL)
        lang = stream.get_audio_lang(ch)
        print "CHANN", ch, lang

stream.signals["event"].connect(show_event)

#del x, vo, ao, stream
#sys.exit(1)
source = stream.get_video_source()
asource = stream.get_audio_source()
post = x.post_init("buffer", video_targets = [vo])

input = post.get_input("video in")
output = post.get_output("video out")
print "All Outputs:", post._post.outputs
for o in post.list_outputs():
    print post.get_output(o)._post_out.port.wire_object
print "---"
print "Input:", input, input.get_port()
print "Output:", output._post_out, output.get_port()
print "STREAM", source, asource, source.get_port(), source.get_type()
print "VO", vo._port

#del x, vo, ao, post, input, output, stream, source, asource
#sys.exit(1)
print "\n\n\n"
# XXX: Activates plugin
#iport = input.get_port()
#print "Input port", iport
source.wire(input)#.get_port())
print vo._port.wire_object

print "Compare out ports", output.get_port(), vo

#stream = x.stream_new(apost.get_audio_inputs()[0], a[0])
stream.open(sys.argv[1])
print "Start playing"
stream.play(time = 60*10)
print "Playing"
print x.list_post_plugins(xine.POST_TYPE_AUDIO_FILTER)
#print post.get_parameters()
print post.set_parameters(ptr = 42)
#print post.set_parameters(gamma = 1.5, contrast = 10.5)
#print post.get_parameters()

#output.unwire()
#source.wire(vo)
#stream.set_parameter(xine.PARAM_SPEED, xine.SPEED_PAUSE)
#post.unwire()
#stream.set_parameter(xine.PARAM_SPEED, xine.SPEED_NORMAL)
xine._debug_show_chain(stream._stream)
print stream._stream.video_source.port
#del x, vo, ao, post, input, output, stream, source, asource
#sys.exit(1)
#stream2 = x.stream_new(ao, vo)
#print stream.slave(stream2)
#print stream.slave(stream2)
#print stream2
print "connect"
kaa.signals["stdin_key_press_event"].connect_weak(key_press, stream)

def print_vpts(stream):
    print "VPTS", stream.get_current_vpts()
    print "Error", stream.get_error(), " - status", stream.get_status()
    print stream.get_pos_length()
    print stream.get_meta_info(xine.META_INFO_VIDEOCODEC)

#timer = notifier.Timer(print_vpts, stream)
#timer.start(1000)

#deint = x.post_init("tvtime", video_targets = [vo])
#deint.set_parameters(method=5)

print "Stream width", stream.get_info(xine.STREAM_INFO_VIDEO_WIDTH)
print "Stream height", stream.get_info(xine.STREAM_INFO_VIDEO_HEIGHT)
print "Stream aspect", stream.get_info(xine.STREAM_INFO_VIDEO_RATIO)
print "Bitrate", stream.get_info(xine.STREAM_INFO_VIDEO_BITRATE)
win.show()
#win.resize((320, 200))
kaa.main()
win.hide()
# Explicitly delete these to test that gc works.
del x, vo, ao, post, input, output, stream, source, asource
