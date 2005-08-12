#!/usr/bin/python

import sys, math, threading, os, time, gc

import kaa
from kaa import xine, display, metadata, notifier, evas

if len(sys.argv) <= 1:
    print "Usage: %s [mrl]" % sys.argv[0]
    sys.exit(1)

# Make argment into mrl if not already
mrl = xine.make_mrl(sys.argv[1])

needs_redraw = False

def say(line):
    if line[0] != "\n":
        sys.stdout.write(" " * 60 + "\r")
    sys.stdout.write(line + "\r")
    sys.stdout.flush()

def handle_keypress_event(key, stream, window):
    channel = stream.get_parameter(xine.PARAM_AUDIO_CHANNEL_LOGICAL)
    lang = stream.get_audio_lang(channel)

    if key == "q":
        stream.stop()
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
        global vo, win, win2, needs_redraw
        if win.get_visible():
            win2.show()
            win.hide()
            stream.deint_post.set_parameters(method = "LinearBlend", framerate_mode = "half_top", pulldown = "none")
            vo.send_gui_data(xine.GUI_SEND_VIDEOWIN_VISIBLE, 0)
        else:
            win.show()
            win2.hide()
            vo.send_gui_data(xine.GUI_SEND_VIDEOWIN_VISIBLE, 1)
            stream.deint_post.set_parameters(method = "LinearBlend", framerate_mode = "full", pulldown = "vektor")
        vo.send_gui_data(xine.GUI_SEND_DRAWABLE_CHANGED, win._window.ptr)
        print "WINDOW TOGGLE"
        needs_redraw = True

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
    global win2, needs_redraw
    if not window.get_visible() and win.get_visible():
        return

    video_width = stream.get_info(xine.STREAM_INFO_VIDEO_WIDTH)
    height = stream.get_info(xine.STREAM_INFO_VIDEO_HEIGHT)
    width = int(math.ceil(height * window.aspect))
    print "\n\nWINDOW ASPECT\n\n\n", aspect, width, height, window.get_size()
    if width and height and (width, height) != window.get_size():
        if window.resize((width, height)):
            say("VO: %dx%d => %dx%d\n" % (video_width, height, width, height))
        window.show()
        #needs_redraw = True

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
def buffer_vo_callback(command, data, window):
    global needs_redraw
    if command == xine.BUFFER_VO_COMMAND_QUERY_REQUEST:
        if not window.get_visible():
            return xine.BUFFER_VO_REQUEST_PASSTHROUGH, -1, -1

        w, h, aspect = data
        if w > window.get_size()[0]:
            w = window.get_size()[0]
        w = 320
        h = 200#int(w / aspect)
        return xine.BUFFER_VO_REQUEST_SEND, w, h #-1, -1
    elif command == xine.BUFFER_VO_COMMAND_QUERY_REDRAW:
        tmp = needs_redraw
        needs_redraw = False
        return tmp
    elif command == xine.BUFFER_VO_COMMAND_SEND:
        global toggle, c, lf
        c+=1
        toggle=1-toggle
        if time.time()-lf > 1:
            print "fps %d\n" % c
            c=0
            lf=time.time()
        notifier.MainThreadCallback(update_evas, data, window)()

def update_evas((width, height, aspect, buffer, unlock_cb), window):
    if window.movie.size_get() != (width, height) or aspect != window.movie.aspect:
        print "RESIZE EVAS", aspect, width, height, window.movie.size_get()
        window.movie.size_set( (width, height) )
        window.movie.aspect = aspect
        w, h = width, height
        #w = min(window.get_size()[0], width)
        #h = int(w / aspect)
        window.movie.resize( (w, h) )
        window.movie.fill_set( (0, 0), (w, h) )
        window.movie.move((0,0))

    window.movie.data_set(buffer, copy = False)
    window.movie.pixels_dirty_set()
    window.get_evas().render()
    unlock_cb()
    return True


win = display.X11Window(size = (50, 50), title = "Kaa Player")
win.set_cursor_hide_timeout(0.5)

x = xine.Xine()
if 0:
    win2 = display.EvasX11Window(gl = True, size = (640, 480), title = "Kaa Player")
    r = win2.get_evas().object_rectangle_add()
    r.color_set((255,255,255,255))
    r.move((0,0))
    r.resize((640, 480))
    r.show()

    win2.bg = win2.get_evas().object_image_add("background.jpg")
    win2.bg.show()
    win2.bg.layer_set(2)
    win2.movie = win2.get_evas().object_image_add()
    win2.movie.aspect = -1
    win2.movie.alpha_set(False)
    #win2.movie.color_set(a=75)
    win2.movie.layer_set(10)
    win2.movie.show()

    cb = notifier.Callback(buffer_vo_callback, win2)
    #vo = x.open_video_driver("buffer", callback = cb, passthrough = x.load_video_output_plugin("xv", window=win))
    vo = x.open_video_driver("xv", window = win)
else:
    vo = x.open_video_driver(window = win)

#x.set_config_value("video.device.xv_colorkey", 2)
#x.set_config_value("video.device.xv_autopaint_colorkey", True)

ao = x.open_audio_driver()
stream = x.new_stream(ao, vo)
#stream.signals["event"].connect_weak(handle_xine_event, win)

kaa.signals["stdin_key_press_event"].connect_weak(handle_keypress_event, stream, win)
win.signals["key_press_event"].connect_weak(handle_keypress_event, stream, win)
if not isinstance(win, display.EvasX11Window):
    win.signals["aspect_changed"].connect_weak(handle_aspect_changed, stream, win)
kaa.signals["idle"].connect_weak(output_status_line, stream, win)

#print "STRAEM souRCE", stream.get_video_source()._post_out.get_port()
#print "STRAEM souRCE", stream.get_audio_source()._post_out.get_port()
#print "Create expand", vo._port, vo._port
#expand = x.post_init("invert", video_targets = [vo])
#print "Done creating expand INPUT", expand.get_default_input()._post_in.port
#print "Done creating expand OUTPUT", expand.get_default_output().get_port()._port.owner
#expand.set_parameters(aspect = 4.0/3.0)

#stream.deint_post = x.post_init("tvtime", video_targets = [vo])#expand.get_default_input()])
#stream.deint_post.get_default_output().wire(expand.get_default_input())
#print "Done creating DEINT OUTPUT", stream.deint_post.get_default_output().get_port()._port.owner
#stream.deint_post.set_parameters(method = "TomsMoComp", enabled = False)

#eq2 = x.post_init("eq2", video_targets = [vo])#expand.get_default_input().get_port()])
#eq2.set_parameters(gamma = 1.2, contrast = 1.1)

#stream.get_video_source()._post_out.wire(expand.get_default_input()._post_in)
#stream.get_video_source().wire(expand.get_default_input())

#print "AUDIO", ao._port
#print "STRAEM souRCE", stream.get_video_source()._post_out.get_port()
#print "STRAEM souRCE", stream.get_audio_source()._post_out.get_port()
#xine._debug_show_chain(stream._stream)
stream.open(mrl)
stream.play()


win.show()
kaa.main()
win.hide()
#del ao, vo, stream, x, win, win2, r, cb, eq2, expand
del stream, ao, vo, x, win
gc.collect()
