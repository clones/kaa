#!/usr/bin/python

# TODO: rewrite me!  This code is testing ground right now.

import sys, math, threading, os, time, gc

import kaa, kaa.input
from kaa import xine, display, metadata, notifier, evas

if len(sys.argv) <= 1:
    print "Usage: %s [mrl]" % sys.argv[0]
    sys.exit(1)

# Make argment into mrl if not already
mrl = xine.make_mrl(sys.argv[1])

needs_redraw = False
draw_osd = True
send_frame = False
osd_alpha = 255

def say(line):
    if line[0] != "\n":
        sys.stdout.write(" " * 60 + "\r")
    sys.stdout.write(line + "\r")
    sys.stdout.flush()

def handle_lirc_event(code, stream, window):
    lirc_map = { "exit": "q", "menu": "m", "select": "space",
                 "ch-": "[", "ch+": "]", "input": "d",
                 "up": "up", "down": "down", "left": "left", "right": "right"
                }

    code = code.lower()
    if code in lirc_map:
        return handle_keypress_event(lirc_map[code], stream, window)


def handle_keypress_event(key, stream, window):
    global osd_alpha, draw_osd, send_frame, needs_redraw

    channel = stream.get_parameter(xine.PARAM_AUDIO_CHANNEL_LOGICAL)
    lang = stream.get_audio_lang(channel)

    if key == "q":
        stream.stop()
        raise SystemExit
    elif key == "r":
        stream.stop()
        stream.open("dvd://")
        stream.play()
    elif key == "f":
        window.set_fullscreen(not window.get_fullscreen())
    elif key in ("m", "menu"):
        stream.send_event(xine.EVENT_INPUT_MENU2)
    elif key == "]":
        stream.send_event(xine.EVENT_INPUT_NEXT)
    elif key == "[":
        stream.send_event(xine.EVENT_INPUT_PREVIOUS)
    elif key == "o":
        draw_osd = not draw_osd
        control("set_osd_visibility", draw_osd)
    elif key == "s":
        send_frame = not send_frame
        control("set_send_frame", send_frame)
    elif key == "d":
        enabled = stream.deint_post.get_parameters()["enabled"]
        stream.deint_post.set_parameters(enabled = not enabled)
        if enabled:
            say("\nDeinterlacing OFF\n")
        else:
            say("\nDeinterlacing ON\n")
    elif key == "p":
        pulldown = stream.deint_post.get_parameters()["pulldown"]
        stream.deint_post.set_parameters(pulldown = {1: "none", 0: "vektor"}[pulldown])

    elif key == "a":
        osd_alpha = max(0, osd_alpha - 10)
        control("set_osd_alpha", osd_alpha)
    elif key == "A":
        osd_alpha = min(255, osd_alpha + 10)
        control("set_osd_alpha", osd_alpha)
    elif key == "v":
        global img2
        img2 = osd.object_image_add("video.png")
        img2.show()
        osd_render()
    elif key == "w":
        global vo, win, win2, needs_redraw
        if win.get_visible():
            win2.show()
            win.hide()
            stream.deint_post.set_parameters(method = "LinearBlend", framerate_mode = "half_top", pulldown = "none")
            print stream.deint_post.get_parameters()
            vo.send_gui_data(xine.GUI_SEND_VIDEOWIN_VISIBLE, 0)
        else:
            win.show()
            win2.hide()
            vo.send_gui_data(xine.GUI_SEND_VIDEOWIN_VISIBLE, 1)
            stream.deint_post.set_parameters(method = "LinearBlend", framerate_mode = "full", pulldown = "vektor")
            print stream.deint_post.get_parameters()
        print "WINDOW TOGGLE"
        needs_redraw = True

    if lang == "menu":
        d = { "up": xine.EVENT_INPUT_UP, "down": xine.EVENT_INPUT_DOWN,
              "left": xine.EVENT_INPUT_LEFT, "right": xine.EVENT_INPUT_RIGHT,
              "enter": xine.EVENT_INPUT_SELECT, "space": xine.EVENT_INPUT_SELECT }
        if key in d:
            stream.send_event(d[key])
    else:
        d = { "up": 60, "down": -60, "left": -10, "right": 10 }
        if key in d:
            stream.seek_relative(d[key])
        elif key == "space":
            speed = stream.get_parameter(xine.PARAM_SPEED)
            if speed == xine.SPEED_PAUSE:
                stream.set_parameter(xine.PARAM_SPEED, xine.SPEED_NORMAL)
            else:
                stream.set_parameter(xine.PARAM_SPEED, xine.SPEED_PAUSE)
                say("\n ==== PAUSE ====\n")

        

def handle_xine_event(event, window):
    stream = event.get_stream()
    #print "EVENT", event.type, event.data

    if event.type == xine.EVENT_UI_SET_TITLE:
        say("New title: %s\n" % event.data["str"])


def handle_aspect_changed(video_width, video_height, aspect, stream, window):
    # Resize window to video dimensions
    global win2, needs_redraw
    if not window.get_visible() and win.get_visible():
        return

    #print "---set crop"
    #stream.set_parameter(xine.PARAM_VO_CROP_LEFT, 300)
    #stream.set_parameter(xine.PARAM_VO_ZOOM_Y, 200)
    #stream.set_parameter(xine.PARAM_VO_CROP_LEFT, 300)
    #stream.set_parameter(xine.PARAM_VO_CROP_RIGHT, 10)
    #stream.set_parameter(xine.PARAM_VO_CROP_TOP, 10)
    #video_width = stream.get_info(xine.STREAM_INFO_VIDEO_WIDTH)
    #video_height= stream.get_info(xine.STREAM_INFO_VIDEO_HEIGHT)
    #width = video_width
    #height = int(math.ceil(width / window.aspect))
    height = video_height
    width = int(math.ceil(height * window.aspect))
    say("VO: %dx%d => %dx%d, aspect=%g\n" % (video_width, video_height, width, height, aspect))
    if width and height and (width, height) != window.get_size():
        if window.resize((width, height)):
            say("VO: RESIZED\n")
        if not window.get_visible():
            window.show()
            #window.set_fullscreen(True)
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
"""
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
"""
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

def new_frame(w, h, ratio, buffer, unlock_frame_cb):
    print "Buffer vo callback", w, h
    unlock_frame_cb()

def osd_configure(w, h, a):
    print "CONFIGURE OSD IN PYTHON", w, h, a
    osd.output_size_set((w, h))
    #osd.viewport_set((0, 0), (w, h))
    osd.render()

def osd_render():
    for region in  osd.render():
        control("osd_invalidate_rect", region)

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

    #cb = notifier.Callback(buffer_vo_callback, win2)
    vo = x.open_video_driver("buffer", passthrough = x.load_video_output_plugin("xv", window=win))
    #vo = x.open_video_driver("xv", window = win)
else:
    l=[]
    import array
    buf = array.array('c', '\x00' * (1024*768*4))
    osd = evas.EvasBuffer((1024, 768), depth = evas.ENGINE_BUFFER_DEPTH_BGRA32, buffer = buf)
    osd.output_size_set((800, 600))
    osd.viewport_set((0, 0), (800, 600))
    #img = osd.object_image_add("background.jpg")
    #img.show()

    osd.fontpath.append(".")
    text = osd.object_text_add(("VeraBd", 24), "This is a Kaa Xine Driver Test")
    text.move((50, 50))
    text.show()

    vo = x.open_video_driver("kaa", control_return = l, 
                             passthrough = x.load_video_output_plugin("xv", window=win),
                             send_frame_cb = new_frame, osd_configure_cb = osd_configure,
                             osd_buffer = buf, osd_stride = 1024*4, osd_rows=768)
    control = l[0]
    #control("set_send_frame_callback", new_frame)
    control("set_send_frame_size", (100, 100))
    control("set_osd_visibility", draw_osd)
    control("set_osd_alpha", 256)
    #vo = x.open_video_driver("opengl", window=win)
    #vo = x.open_video_driver("xshm", window=win)
    vo = x.open_video_driver("xv", window = win)

#x.set_config_value("video.device.xv_colorkey", 2)
#x.set_config_value("video.device.xv_autopaint_colorkey", True)

ao = x.open_audio_driver()
stream = x.new_stream(ao, vo)

kaa.input.lirc.init()
kaa.signals["stdin_key_press_event"].connect_weak(handle_keypress_event, stream, win)
if "lirc" in kaa.signals:
    kaa.signals["lirc"].connect_weak(handle_lirc_event, stream, win)
win.signals["key_press_event"].connect_weak(handle_keypress_event, stream, win)
if "aspect_changed" in win.signals:
    win.signals["aspect_changed"].connect_weak(handle_aspect_changed, stream, win)
kaa.signals["idle"].connect_weak(output_status_line, stream, win)

stream.deint_post = x.post_init("tvtime", video_targets = [vo])
stream.deint_post.set_parameters(method = "GreedyH", enabled = True)
#stream.get_video_source().wire(stream.deint_post.get_default_input())
stream.deint_post.set_parameters(cheap_mode = True)
#stream.deint_post.set_parameters(framerate_mode = "half_top")
#print stream.deint_post.get_parameters_desc()

print x.list_post_plugins()
#expand = x.post_init("expand", video_targets = [vo])
expand = x.post_init("scale", video_targets = [stream.deint_post.get_default_input().get_port()])
expand.set_parameters(w = 640, h = -2)
#print expand.get_parameters_desc()
#expand = x.post_init("expand", video_targets = [vo])
#expand = x.post_init("expand", video_targets = [stream.deint_post.get_default_input().get_port()])
stream.get_video_source().wire(expand.get_default_input())

#eq2 = x.post_init("eq2", video_targets = [stream.deint_post.get_default_input().get_port()])
#eq2.set_parameters(gamma = 1.2, contrast = 1.1)

# Test unwire
#stream.get_video_source().wire(eq2.get_default_input())
#eq2.unwire()

#assert(stream.get_video_source().get_port() == stream.deint_post.get_default_input().get_port())

xine._debug_show_chain(stream._obj)

stream.open(mrl)
stream.play()

#stream.set_parameter(xine.PARAM_SPEED, xine.SPEED_SLOW_4)
#stream.set_parameter(xine.PARAM_VO_ZOOM_X, 110)
#stream.set_parameter(xine.PARAM_VO_ZOOM_Y, 110)
#stream.set_parameter(xine.PARAM_VO_CROP_LEFT, 100)
#stream.set_parameter(xine.PARAM_VO_CROP_RIGHT, 10)
#stream.set_parameter(xine.PARAM_VO_CROP_TOP, 10)

#win.resize((640, 480))
#win.show()
#win.set_fullscreen(True)

kaa.main()
win.hide()
del stream, ao, vo, x, win, expand#, eq2
#del win2, r
gc.collect()
