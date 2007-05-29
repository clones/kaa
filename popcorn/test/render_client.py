# Xine render client for render_manager.py
#   Usage: python render_client.py /tmp/fifo1 video.avi
# 
# Render manager must be monitoring /tmp/fifo1
#

import sys, os, sys
import kaa.display, kaa.evas, kaa.xine, kaa, kaa.input.stdin

def key(key):
    if key == 'q':
        sys.exit(0)
    elif key == 'm':
        stream.send_event(kaa.xine.EVENT_INPUT_MENU2)
    
    if stream.is_in_menu:
        d = { "up": kaa.xine.EVENT_INPUT_UP, "down": kaa.xine.EVENT_INPUT_DOWN,
              "left": kaa.xine.EVENT_INPUT_LEFT, "right": kaa.xine.EVENT_INPUT_RIGHT,
              "enter": kaa.xine.EVENT_INPUT_SELECT, "space": kaa.xine.EVENT_INPUT_SELECT }
        if key in d:
            stream.send_event(d[key])
    else:
        d = { "up": 60, "down": -60, "left": -10, "right": 10 }
        if key in d:
            stream.seek_relative(d[key])
        if key == "space":
            if stream.get_parameter(kaa.xine.PARAM_SPEED) == kaa.xine.SPEED_PAUSE:
                stream.set_parameter(kaa.xine.PARAM_SPEED, kaa.xine.SPEED_NORMAL)
            else:
                stream.set_parameter(kaa.xine.PARAM_SPEED, kaa.xine.SPEED_PAUSE)


def handle_xine_event(event):
    stream = event.get_stream()
    if event.type == kaa.xine.EVENT_UI_NUM_BUTTONS:
        stream.is_in_menu = event.data["num_buttons"] > 0


fd = os.open(sys.argv[1], os.O_RDWR | os.O_NONBLOCK)

l = []
xine = kaa.xine.Xine()
vo = xine.open_video_driver('kaa', passthrough = 'none', control_return = l, notify_fd = fd)
control = l[0]
control('set_notify_frame', True)
try:
    ao = xine.open_audio_driver()
except:
    # Audio device in use, use dummy driver.
    ao = xine.open_audio_driver('none')

stream = xine.new_stream(ao, vo)
stream.signals["event"].connect(handle_xine_event)
stream.is_in_menu = False

deint = xine.post_init('tvtime', video_targets = [vo])
deint.set_parameters(method = 'LinearBlend', enabled = True, chroma_filter = False, cheap_mode = False)
stream.get_video_source().wire(deint.get_default_input())

stream.open(sys.argv[2])
stream.play()

kaa.signals['stdin_key_press_event'].connect(key)
kaa.main()
# We need to break cycles so dealloc handlers get called on shutdown.
del deint, vo, ao, stream, xine
