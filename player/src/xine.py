import sys, os, md5, shm, time, fcntl, struct
import kaa
from kaa import notifier, display
try:
    from kaa import xine
except ImportError:
    xine = None

# player base
from base import *

BUFFER_UNLOCKED = 0x10
BUFFER_LOCKED = 0x20

class XinePlayerChild(object):

    def __init__(self, instance_id):
        self._xine = xine.Xine()
        self._stream = self._vo = self._ao = None

        self._osd_shmkey = int(md5.md5(instance_id + "osd").hexdigest()[:7], 16)
        self._frame_shmkey = int(md5.md5(instance_id + "frame").hexdigest()[:7], 16)
        self._osd_shmem = self._frame_shmem = None

        self._x11_window_size = 0, 0
        self._x11_last_aspect = -1
        self._status = notifier.WeakTimer(self._status_output)
        self._status.start(0.1)
        self._status_last = None

        monitor = kaa.notifier.WeakSocketDispatcher(self._handle_line)
        monitor.register(sys.stdin.fileno())
        flags = fcntl.fcntl(sys.stdin.fileno(), fcntl.F_GETFL)
        fcntl.fcntl(sys.stdin.fileno(), fcntl.F_SETFL, flags | os.O_NONBLOCK)


    def _send_command(self, command, *args):
        sys.stderr.write("!" + repr( (command, args) ) + "\n")


    def _handle_line(self):
        data = sys.stdin.read()
        if len(data) == 0:
            # Parent likely died.
            self._handle_command_die()

        for line in data.splitlines():
            command, args = eval(line)
            reply = getattr(self, "_handle_command_" + command)(*args)


    def _status_output(self):
        """
        Outputs stream status information.
        """
        if not self._stream:
            return

        t = self._stream.get_pos_length()
        status = self._stream.get_status()
        speed = self._stream.get_parameter(xine.PARAM_SPEED)

        # Line format: pos time length status speed
        # Where status is one of XINE_STATUS_ constants, and speed
        # is one of XINE_SPEED constants.
        cur_status = (t[0], t[1], t[2], status, speed)

        if cur_status != self._status_last:
            #sys.stderr.write("S: %s\n" % line)
            self._status_last = cur_status
            self._send_command("status", *cur_status)


    def _handle_command_window_changed(self, wid, size, visible, exposed_regions):
        self._x11_window_size = size
        self._wid = wid
        if self._vo:
            self._vo.send_gui_data(xine.GUI_SEND_VIDEOWIN_VISIBLE, visible)
            self._vo.send_gui_data(xine.GUI_SEND_DRAWABLE_CHANGED, wid)
        

    def _x11_frame_output_cb(self, width, height, aspect):
        #print "Frame output", width, height, aspect
        w, h, a = self._xine._get_vo_display_size(width, height, aspect)
        if abs(self._x11_last_aspect - a) > 0.01:
            print "VO: %dx%d -> %dx%d" % (width, height, w, h)
            self._send_command("resize", (w, h))
            self._x11_last_aspect = a
        if self._x11_window_size != (0, 0):
            w, h = self._x11_window_size

        return (0, 0), (0, 0), (w, h), 1.0


    def _x11_dest_size_cb(self, width, height, aspect):
        # TODO:
        #if not self._x11_window_visibile:
        #    w, h, a = self._get_vo_display_size(width, height, aspect)
        #else:
        #    w, h = self._x11_window_size
        w, h = self._x11_window_size
        return (w, h), 1.0


    def _osd_configure(self, width, height, aspect):
        frame_shmem_size = width * height * 4 + 16
        #if self._frame_shmem and self._frame_shmem.size != frame_shmem_size:
        if not self._frame_shmem:
            self._frame_shmem = shm.create_memory(self._frame_shmkey, frame_shmem_size)
            self._frame_shmem.attach()
        if not self._osd_shmem:
            self._osd_shmem = shm.create_memory(self._osd_shmkey, 2000 * 2000 * 4 + 16)
            self._osd_shmem.attach()
            self._osd_shmem.write(chr(BUFFER_UNLOCKED))


        # FIXME: don't hardcore buffer dimensions
        self._send_command("osd_configure", width, height, aspect, 2000, 2000)
        return self._osd_shmem.addr + 16, 2000 * 4, self._frame_shmem.addr


    def _handle_command_setup(self, wid):
        if self._stream:
            return

        self._wid = wid
        self._ao = self._xine.open_audio_driver()

        control_return = []
        self._vo = self._xine.open_video_driver("kaa", control_return = control_return,
                    passthrough = "xv", wid = wid, osd_configure_cb = notifier.WeakCallback(self._osd_configure),
#                    osd_buffer = self._osd_shmem.addr + 16, osd_stride = 2000 * 4, osd_rows = 2000,
#        self._vo = self._xine.open_video_driver("xv", wid = wid,
                    frame_output_cb = notifier.WeakCallback(self._x11_frame_output_cb),
                    dest_size_cb = notifier.WeakCallback(self._x11_dest_size_cb))
#        self._vo = self._xine.open_video_driver("none")
        self._driver_control = control_return[0]

        self._stream = self._xine.new_stream(self._ao, self._vo) 
        self._stream.signals["event"].connect_weak(self.handle_xine_event)


        # FIXME: plugin stuff should be exposed via api, or configurable
        # somehow.

        #self._noise_post = self._xine.post_init("noise", video_targets = [self._vo])
        #self._noise_post.set_parameters(luma_strength = 3, quality = "temporal")
        #self._stream.get_video_source().wire(self._noise_post.get_default_input())

        #self._deint_post = self._xine.post_init("tvtime", video_targets = [self._expand_post.get_default_input()])
        self._deint_post = self._xine.post_init("tvtime", video_targets = [self._vo])
        self._deint_post.set_parameters(method = "GreedyH", chroma_filter = False, framerate_mode="half_top")
        #self._deint_post.set_parameters(method = "LinearBlend", cheap_mode = True)#, chroma_filter = True)

        self._stream.get_video_source().wire(self._deint_post.get_default_input())
        #self._expand_post = self._xine.post_init("expand", video_targets = [self._vo])
        self._expand_post = self._xine.post_init("expand", video_targets = [self._deint_post.get_default_input()])
        self._expand_post.set_parameters(enable_automatic_shift = True)
        self._stream.get_video_source().wire(self._expand_post.get_default_input())

        self._goom_post = self._xine.post_init("goom", video_targets = [self._vo], audio_targets=[self._ao])

        #self._driver_control("set_passthrough", False)
        return self._stream


    def _handle_command_open(self, mrl):
        try:
            self._stream.open(mrl)
            if not self._stream.get_info(xine.STREAM_INFO_HAS_VIDEO):
                self._stream.get_audio_source().wire(self._goom_post.get_default_input())
            else:
                self._stream.get_audio_source().wire(self._ao)
            xine._debug_show_chain(self._stream._obj)
        except xine.XineError:
            # TODO: ipc this
            print "Open failed:", self._stream.get_error()
        self._send_command("stream_info", self.get_stream_info())


    def get_xine(self):
        return self._xine

    def get_stream(self):
        return self._stream


    def get_stream_info(self):
        if not self._stream:
            return {}

        info = {
            "vfourcc": self._stream.get_info(xine.STREAM_INFO_VIDEO_FOURCC),
            "afourcc": self._stream.get_info(xine.STREAM_INFO_AUDIO_FOURCC),
            "vcodec": self._stream.get_meta_info(xine.META_INFO_VIDEOCODEC),
            "acodec": self._stream.get_meta_info(xine.META_INFO_AUDIOCODEC),
            "width": self._stream.get_info(xine.STREAM_INFO_VIDEO_WIDTH),
            "height": self._stream.get_info(xine.STREAM_INFO_VIDEO_HEIGHT),
            "aspect": self._stream.get_info(xine.STREAM_INFO_VIDEO_RATIO) / 10000.0,
            "fps": self._stream.get_info(xine.STREAM_INFO_FRAME_DURATION),
            "length": self._stream.get_length(),
        }
        if self._x11_last_aspect != -1:
            # Use the aspect ratio as given to the frame output callback
            # as it tends to be more reliable (particularly for DVDs).
            info["aspect"] = self._x11_last_aspect
        if info["aspect"] == 0 and info["height"] > 0:
            info["aspect"] = info["width"] / float(info["height"])
        if info["fps"]:
            info["fps"] = 90000.0 / info["fps"]
        return info


    def handle_xine_event(self, event):
        if len(event.data) > 1:
            del event.data["data"]
        print "EVENT", event.type, event.data
        if event.type == xine.EVENT_UI_CHANNELS_CHANGED:
            self._send_command("stream_info", self.get_stream_info())
        self._send_command("xine_event", event.type, event.data)


    def _handle_command_osd_update(self, alpha, visible, invalid_regions):
        if not self._osd_shmem:
            return

        if alpha:
            self._driver_control("set_osd_alpha", alpha)
        if visible:
            self._driver_control("set_osd_visibility", visible)
        if invalid_regions:
            self._driver_control("osd_invalidate_rect", invalid_regions)
        self._osd_shmem.write(chr(BUFFER_UNLOCKED))


    def _handle_command_play(self):
        status = self._stream.get_status()
        if status == xine.STATUS_PLAY:
            self._stream.set_parameter(xine.PARAM_SPEED, xine.SPEED_NORMAL)
        elif status == xine.STATUS_STOP:
            self._stream.play()

    def _handle_command_pause(self):
        self._stream.set_parameter(xine.PARAM_SPEED, xine.SPEED_PAUSE)

    def _handle_command_seek(self, whence, value):
        if whence == 0:
            self._stream.seek_relative(value)
        elif whence == 1:
            self._stream.seek_absolute(value)
        elif whence == 2:
            self._stream.play(pos = value)


    def _handle_command_die(self):
        self._handle_command_stop()
        sys.exit(0)


    def _handle_command_stop(self):
        if self._stream:
            self._stream.stop()
            self._stream.close()


    def _handle_command_frame_output(self, vo, notify, size):
        if vo != None:
            self._driver_control("set_passthrough", vo)
        if notify != None:
            if notify:
                print "FRAME RATE MODE HALF TOP"
                self._deint_post.set_parameters(framerate_mode="half_top")
            else:
                print "FRAME RATE MODE FULL"
                self._deint_post.set_parameters(framerate_mode="full")
            self._driver_control("set_notify_frame", notify)
        if size != None:
            self._driver_control("set_notify_frame_size", size)


    def _handle_command_input(self, input):
        self._stream.send_event(input)






class XinePlayer(MediaPlayer):

    _instance_count = 0

    def __init__(self):
        super(XinePlayer, self).__init__()
        self._instance_id = "kaaxine-%d-%d" % (os.getpid(), XinePlayer._instance_count)
        XinePlayer._instance_count += 1

        self._osd_shmkey = int(md5.md5(self._instance_id + "osd").hexdigest()[:7], 16)
        self._frame_shmkey = int(md5.md5(self._instance_id + "frame").hexdigest()[:7], 16)
        self._osd_shmem = self._frame_shmem = None
        #kaa.signals["shutdown"].connect_weak(self._remove_shmem)
        self._check_new_frame_timer = kaa.notifier.WeakTimer(self._check_new_frame)

        self._is_in_menu = False
        self._state_data = None
        self._stream_info = {}
        self._position = 0.0
        self._cur_frame_output_mode = [True, False, None] # vo, shmem, size

        self._spawn()


    def _remove_shmem(self):
        if self._osd_shmem:
            try:
                self._osd_shmem.detach()
                shm.remove_memory(self._osd_shmem.shmid)
            except shm.error:
                # Probably already deleted by child
                pass
            self._osd_shmem = None

        if self._frame_shmem:
            try:
                self._frame_shmem.detach()
                shm.remove_memory(self._frame_shmem.shmid)
            except shm.error:
                pass
            self._frame_shmem = None
        

    def _spawn(self):
        # Launch self (-u is unbuffered stdout)
        self._process = notifier.Process("%s -u %s" % (sys.executable, __file__))
        self._process.signals["stdout"].connect_weak(self._handle_line)
        self._process.signals["stderr"].connect_weak(self._handle_line)
        self._process.signals["completed"].connect_weak(self._exited)
        self._process.set_stop_command(notifier.WeakCallback(self._end_child))
        self._process.start(str(self._instance_id))



    def _send_command(self, command, *args):
        s = repr((command, args))
        self._process.write(s + "\n")


    def _end_child(self):
        self._send_command("die")

    def die(self):
        if self._process:
            self._process.stop()


    def _exited(self, exitcode):
        self._state = STATE_NOT_RUNNING
        self._remove_shmem()
        self.signals["quit"].emit()


    def _handle_line(self, line):
        if line and line[0] == "!":
            command, args = eval(line[1:])
            getattr(self, "_handle_command_" + command)(*args)
        else:
            print "CHILD[%d]: %s" % (self._process.child.pid, line)


    def _handle_command_status(self, pos, time, length, status, speed):
        old_pos = self._position
        self._position = float(time)
        self._stream_info["length"] = length

        if status == 2:
            if self.get_state() not in (STATE_PAUSED, STATE_PLAYING):
                self.signals["start"].emit()
            if speed == xine.SPEED_PAUSE and self.get_state() != STATE_PAUSED:
                self._state = STATE_PAUSED
                self.signals["pause_toggle"].emit()
                self.signals["pause"].emit()
            elif speed > xine.SPEED_PAUSE and self.get_state() != STATE_PLAYING:
                self._state = STATE_PLAYING
                if self.get_state() == STATE_PAUSED:
                    self.signals["pause_toggle"].emit()
                self.signals["play"].emit()

            if self._position - old_pos < 0 or self._position - old_pos > 1:
                self.signals["seek"].emit(self._position)
        elif status in (0, 1):
            if self.get_state() in (STATE_PAUSED, STATE_PLAYING):
                # Stream ended.
                self._state = STATE_IDLE 
                self.signals["end"].emit()


    def _handle_command_osd_configure(self, width, height, aspect, buffer_width, buffer_height):
        if not self._osd_shmem:
            shmid = shm.getshmid(self._osd_shmkey)
            if shmid:
                self._osd_shmem = shm.memory(shmid)
                self._osd_shmem.attach()
        if not self._frame_shmem:
            shmid = shm.getshmid(self._frame_shmkey)
            if shmid:
                self._frame_shmem = shm.memory(shmid)
                self._frame_shmem.attach()

        # TODO: remember these values and emit them to new connections to
        # this signal after this point.
        self.signals["osd_configure"].emit(width, height, self._osd_shmem.addr + 16, 
                                           buffer_width, buffer_height)
 
            
    def _handle_command_resize(self, size):
        pass
        #self._window.resize(size)


    def _handle_command_stream_info(self, info):
        changed = info != self._stream_info
        self._stream_info = info
 
        if self._state == STATE_OPENING:
            self._state = STATE_IDLE
            self._send_command("play")
            self.set_frame_output_mode()

        if changed:
            self.signals["stream_changed"].emit()

    def _handle_command_xine_event(self, event, data):
        if event == xine.EVENT_UI_NUM_BUTTONS:
            self._is_in_menu = data["num_buttons"] > 0


    def _handle_window_visibility_event(self):
        self._send_command("window_changed", self._window.get_id(), self._window.get_size(), self._window.get_visible(), [])

    def _handle_window_expose_event(self, regions):
        self._send_command("window_changed", self._window.get_id(), self._window.get_size(), self._window.get_visible(), regions)

    def _handle_window_configure_event(self, pos, size):
        self._send_command("window_changed", self._window.get_id(), size, self._window.get_visible(), [])

    def _show_window(self):
        if self._window:
            self._window.show()
            self._handle_window_visibility_event()


    def open(self, mrl):
        scheme, path = parse_mrl(mrl)
        if scheme not in self.get_supported_schemes():
            raise ValueError, "Unsupported mrl scheme '%s'" % scheme

        self._mrl = "%s:%s" % (scheme, path)
        # Open with kaa.metadata
        self.signals["open"].emit()


    def play(self):
        if self.get_state() == STATE_PAUSED:
            self._send_command("play")
            return

        if self.get_state() == STATE_NOT_RUNNING:
            if self._window == None:
                # Use the user specified size, or some sensible default.
                win_size = self._size or (640, 480)
                window = display.X11Window(size = win_size, title = "Movie Window")
                self.set_window(window)

        # TODO: no window
        self._send_command("setup", self._window.get_id())

        self._position = 0.0
        self._send_command("open", self._mrl)
        self._state = STATE_OPENING 
 

    def pause(self):
        self._send_command("pause")
        

    def pause_toggle(self):
        if self.get_state() == STATE_PLAYING:
            self.pause()
        else:
            self.play()
  
    def stop(self):
        self._send_command("stop")
        

    def seek_relative(self, offset):
        self._send_command("seek", 0, offset)


    def seek_absolute(self, position):
        self._send_command("seek", 1, position)


    def seek_percentage(self, percent):
        pos = (percent / 100.0) * 65535
        self._send_command("seek", 2, pos)

    def get_info(self):
        return self._stream_info


    def osd_update(self, alpha = None, visible = None, invalid_regions = None):
        self._send_command("osd_update", alpha, visible, invalid_regions)
        

    def osd_can_update(self):
        if not self._osd_shmem:
            return False

        try:
            if ord(self._osd_shmem.read(1)) == BUFFER_UNLOCKED:
                return True
        except:
            self._osd_shmem = None

        return False

    def set_frame_output_mode(self, vo = None, notify = None, size = None):
        if vo != None:
            self._cur_frame_output_mode[0] = vo
        if notify != None:
            self._cur_frame_output_mode[1] = notify
        if size != None:
            self._cur_frame_output_mode[2] = size

        if self.get_state() in (STATE_NOT_RUNNING, STATE_OPENING):
            return

        vo, notify, size = self._cur_frame_output_mode

        if notify:
            self._check_new_frame_timer.start(0.01)
        else:
            self._check_new_frame_timer.stop()

        self._send_command("frame_output", vo, notify, size)


    def set_window(self, window):
        old_window = self._window
        super(XinePlayer, self).set_window(window)

        if old_window and old_window != self._window:
            # Disconnect signals from existing window.
            old_window.signals["configure_event"].disconnect(self._handle_window_configure_event)
            old_window.signals["map_event"].disconnect(self._handle_window_visibility_event)
            old_window.signals["unmap_event"].disconnect(self._handle_window_visibility_event)
            old_window.signals["expose_event"].disconnect(self._handle_window_expose_event)

        if window:
            window.signals["configure_event"].connect_weak(self._handle_window_configure_event)
            window.signals["map_event"].connect_weak(self._handle_window_visibility_event)
            window.signals["unmap_event"].connect_weak(self._handle_window_visibility_event)
            window.signals["expose_event"].connect_weak(self._handle_window_expose_event)

    def get_position(self):
        return self._position

    def get_player_id(self):
        return "xine"


    def _check_new_frame(self):
        if not self._frame_shmem:
            return

        try:
            lock, width, height, aspect = struct.unpack("hhhd", self._frame_shmem.read(16))
        except:
            self._frame_shmem = None
            return

        if lock & BUFFER_UNLOCKED:
            return
 
        if width > 0 and height > 0 and aspect > 0:
            self.signals["frame"].emit(width, height, aspect, self._frame_shmem.addr + 16, "bgr32")


    def unlock_frame_buffer(self):
        try:
            self._frame_shmem.write(chr(BUFFER_UNLOCKED))
        except shm.error:
            self._frame_shmem = None


    def nav_command(self, input):
        map = {
            "up": xine.EVENT_INPUT_UP,
            "down": xine.EVENT_INPUT_DOWN,
            "left": xine.EVENT_INPUT_LEFT,
            "right": xine.EVENT_INPUT_RIGHT,
            "select": xine.EVENT_INPUT_SELECT,
            "prev": xine.EVENT_INPUT_PREVIOUS,
            "next": xine.EVENT_INPUT_NEXT,
            "angle_prev": xine.EVENT_INPUT_ANGLE_PREVIOUS,
            "angle_next": xine.EVENT_INPUT_ANGLE_NEXT,
            "menu1": xine.EVENT_INPUT_MENU1,
            "menu2": xine.EVENT_INPUT_MENU2,
            "menu3": xine.EVENT_INPUT_MENU3,
            "menu4": xine.EVENT_INPUT_MENU4,
            "0": xine.EVENT_INPUT_NUMBER_0,
            "1": xine.EVENT_INPUT_NUMBER_1,
            "2": xine.EVENT_INPUT_NUMBER_2,
            "3": xine.EVENT_INPUT_NUMBER_3,
            "4": xine.EVENT_INPUT_NUMBER_4,
            "5": xine.EVENT_INPUT_NUMBER_5,
            "6": xine.EVENT_INPUT_NUMBER_6,
            "7": xine.EVENT_INPUT_NUMBER_7,
            "8": xine.EVENT_INPUT_NUMBER_8,
            "9": xine.EVENT_INPUT_NUMBER_9
        }
        if input in map:
            self._send_command("input", map[input])


    def is_in_menu(self):
        return self._is_in_menu 

def get_capabilities():
    caps = (CAP_VIDEO, CAP_AUDIO, CAP_OSD, CAP_CANVAS, CAP_DVD, CAP_DVD_MENUS,
           CAP_DYNAMIC_FILTERS, CAP_VARIABLE_SPEED, CAP_VISUALIZATION,
           CAP_DEINTERLACE)
    schemes = [ "file", "fifo", "dvd", "vcd", "cdda", "http", "tcp", "udp",
                "rtp", "smb", "mms", "pnm", "rtsp" ]
    exts = ["mpg", "mpeg", "iso"]  # FIXME: complete
    return caps, schemes, exts


if __name__ == "__main__":
    # We're being called as a child.
    import gc
    #gc.set_debug(gc.DEBUG_COLLECTABLE | gc.DEBUG_UNCOLLECTABLE | gc.DEBUG_INSTANCES | gc.DEBUG_OBJECTS)
    player = XinePlayerChild(sys.argv[1])
    kaa.main()

    # Remove shared memory.  We don't detach right away, because the vo
    # thread might still be running, and it will crash if it tries to write
    # to that memory.
    if player._osd_shmem:
        shm.remove_memory(player._osd_shmem.shmid)
    if player._frame_shmem:
        shm.remove_memory(player._frame_shmem.shmid)

    # Force garbage collection for testing.
    del player
    gc.collect()


else:
    if xine:
        register_player("xine", XinePlayer, get_capabilities)

