#!/usr/bin/python

import sys, math, threading, os, time, gc

import kaa
from kaa import xine, display, metadata, notifier, evas

if len(sys.argv) <= 1:
    print "Usage: %s [mrl]" % sys.argv[0]
    sys.exit(1)

# Make argment into mrl if not already
mrl = xine.make_mrl(sys.argv[1])

def say(line):
    if line[0] != "\n":
        sys.stdout.write(" " * 60 + "\r")
    sys.stdout.write(line + "\r")
    sys.stdout.flush()

def handle_keypress_event(key, stream, window):
    channel = stream.get_parameter(xine.PARAM_AUDIO_CHANNEL_LOGICAL)
    lang = stream.get_audio_lang(channel)

    if key == "q":
        print "\n\nExiting\n\n"
        stream.stop()
        print "\n\nDone Exiting\n\n"
        raise SystemExit
    elif key == "f":
        window.set_fullscreen(not window.get_fullscreen())
    elif key in ("m", "menu"):
        stream.send_event(xine.EVENT_INPUT_MENU2)
    elif key == "space":
        speed = stream.get_parameter(xine.PARAM_SPEED)
        if speed == xine.SPEED_PAUSE:
            stream.set_parameter(xine.PARAM_SPEED, xine.SPEED_NORMAL)
        else:
            stream.set_parameter(xine.PARAM_SPEED, xine.SPEED_PAUSE)
            say("\n ==== PAUSE ====\n")
    elif key == "]":
        stream.send_event(xine.EVENT_INPUT_NEXT)
    elif key == "[":
        stream.send_event(xine.EVENT_INPUT_PREVIOUS)
    elif key == "d":
        enabled = stream.deint_post.get_parameters()["enabled"]
        stream.deint_post.set_parameters(enabled = not enabled)
        if enabled:
            say("\nDeinterlacing OFF\n")
        else:
            say("\nDeinterlacing ON\n")

    elif key == "a":
        global vo_xv, win, win2
        if win.get_visible():
            win2.show()
            win.hide()
        else:
            win.show()
            win2.hide()
            vo_xv._port.send_gui_data(xine.GUI_SEND_DRAWABLE_CHANGED, win._window.ptr)
            vo_xv._port.send_gui_data(xine.GUI_SEND_VIDEOWIN_VISIBLE, 1)
        

    if lang == "menu":
        d = { "up": xine.EVENT_INPUT_UP, "down": xine.EVENT_INPUT_DOWN,
              "left": xine.EVENT_INPUT_LEFT, "right": xine.EVENT_INPUT_RIGHT,
              "enter": xine.EVENT_INPUT_SELECT }
        if key in d:
            stream.send_event(d[key])
    else:
        d = { "up": 60, "down": -60, "left": -10, "right": 10 }
        if key in d:
            stream.seek_relative(d[key])

        

def handle_xine_event(event, window):
    stream = event.get_stream()
    #print "EVENT", event.type, event.data

    if event.type == xine.EVENT_UI_SET_TITLE:
        say("New title: %s\n" % event.data["str"])


def handle_aspect_changed(aspect, stream, window):
    # Resize window to video dimensions
    video_width = stream.get_info(xine.STREAM_INFO_VIDEO_WIDTH)
    height = stream.get_info(xine.STREAM_INFO_VIDEO_HEIGHT)
    width = int(math.ceil(height * window.aspect))
    print "\n\nWINDOW ASPECT\n\n\n", aspect, width, height, window.get_size()
    if width and height and (width, height) != window.get_size():
        if window.resize((width, height)):
            say("VO: %dx%d => %dx%d\n" % (video_width, height, width, height))
        window.show()

def output_status_line(stream, window):
    if stream.get_parameter(xine.PARAM_SPEED) == xine.SPEED_PAUSE:
        return
    pos, time, length = stream.get_pos_length()
    if length:
        percent = (time/length)*100
    else:
        percent = 0
    say("Position: %.1f / %.1f (%.1f%%)" % (time, length, percent))


def render():
    print "RENDER FROM MAIN THREAD\n\n"

toggle=1
c=0
lf=0
def foo(width, height, aspect, buffer, window):
    global toggle, c, lf
    c+=1
    toggle=1-toggle
    if time.time()-lf > 1:
        print threading.currentThread(), "fps %d\n" % c
        c=0
        lf=time.time()
    return 1
    if not window.get_visible():
        return True
    if window.movie.size_get() != (width, height):
        print "RESIZE", width, height, threading.currentThread()
        window.movie.size_set( (width, height) )
        w, h = width, height
        window.movie.resize( (w, h) )
        window.movie.fill_set( (0, 0), (w, h) )
        window.movie.move((0,0))

    window.movie.pixels_import(buffer, width, height, evas.PIXEL_FORMAT_YUV420P_601)
    window.movie.pixels_dirty_set()
    notifier.MainThreadCallback(window.get_evas().render)()
    return True


win = display.X11Window(size = (50, 50), title = "Kaa Player")
win.set_cursor_hide_timeout(0.5)

x = xine.Xine()
if 1:
    win2 = display.EvasX11Window(gl = False, size = (640, 480), title = "Kaa Player")
    r = win2.get_evas().object_rectangle_add()
    r.color_set((255,255,255,255))
    r.move((0,0))
    r.resize((640, 480))
    r.show()

    win2.bg = win2.get_evas().object_image_add("background.jpg")
    win2.bg.show()
    win2.bg.layer_set(2)
    win2.movie = win2.get_evas().object_image_add()
    win2.movie.alpha_set(True)
    #win.movie.color_set(a=50)
    win2.movie.layer_set(10)
    win2.movie.show()

    cb = notifier.Callback(foo, win2)
    #cb = notifier.MainThreadCallback(foo, win2)
    #cb.set_async(False)
    #vo_xv = x.open_video_driver(window = win)
    vo = x.open_video_driver("buffer", callback = cb, passthrough = x.load_video_output_plugin("xv", window=win))
    #vo = x.open_video_driver("xv", window = win)
else:
    vo = x.open_video_driver(window = win)

ao = x.open_audio_driver()
stream = x.new_stream(ao, vo)
stream.signals["event"].connect_weak(handle_xine_event, win)

kaa.signals["stdin_key_press_event"].connect_weak(handle_keypress_event, stream, win)
win.signals["key_press_event"].connect_weak(handle_keypress_event, stream, win)
if not isinstance(win, display.EvasX11Window):
    win.signals["aspect_changed"].connect_weak(handle_aspect_changed, stream, win)
#kaa.signals["idle"].connect_weak(output_status_line, stream, win)

stream.deint_post = x.post_init("tvtime", video_targets = [vo])
print stream.deint_post.get_parameters_desc()["framerate_mode"]
stream.deint_post.set_parameters(method = "GreedyH")
stream.get_video_source().wire(stream.deint_post.get_default_input())

#print vo, vo.get_driver(), vo.get_driver()._driver.owner, vo.get_driver().get_port()
stream.open(mrl)
stream.play()

win.show()
kaa.main()
win.hide()
print win2._display._display, win._display._display, win2.get_evas()._dependencies
del ao, vo, stream, x, win, win2, r, cb
gc.collect()
