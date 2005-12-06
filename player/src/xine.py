import sys, os, md5, shm, time, fcntl
import kaa
from kaa import notifier, display, xine
# player base
from base import *


class XinePlayerChild(object):

    def __init__(self, shmkey):
        self._xine = xine.Xine()
        self._stream = self._vo = self._ao = None

        self._shmkey = int(shmkey)
        self._osd_buffer = None

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
        for line in sys.stdin.read().splitlines():
            command, args = eval(line)
            reply = getattr(self, "_handle_command_" + command)(*args)


    def _status_output(self):
        """
        Outputs stream status information to stdout, to be parsed by parent.
        We don't use IPC here because of the overhead.  This is called every
        0.1 seconds, and each IPC call has a fair amount of overhead.
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


    def _handle_command_window_resized(self, cur_size):
        self._x11_window_size = cur_size
        self._vo.send_gui_data(xine.GUI_SEND_VIDEOWIN_VISIBLE, 1)
        self._vo.send_gui_data(xine.GUI_SEND_DRAWABLE_CHANGED, self._wid)
        

    def _x11_frame_output_cb(self, width, height, aspect):
        w, h, a = self._xine._get_vo_display_size(width, height, aspect)
        if abs(self._x11_last_aspect - a) > 0.01:
            print "VO: %dx%d -> %dx%d" % (width, height, w, h)
            self._send_command("resize", (w, h))
            self._x11_last_aspect = a
        if self._x11_window_size != (0, 0):
            w, h = self._x11_window_size

        return (0, 0), (0, 0), (w, h), 1.0


    def _x11_dest_size_cb(self, width, height, aspect):
        print "Dest size cb"
        #if not self._x11_window_visibile:
        #    w, h, a = self._get_vo_display_size(width, height, aspect)
        #else:
        #    w, h = self._x11_window_size
        w, h = self._x11_window_size
        return (w, h), 1.0


    def _osd_configure(self, width, height, aspect):
        # FIXME: don't hardcore buffer dimensions
        #sys.stderr.write("OSD: %d %d %f %d %d\n" % (width, height, aspect, 2000, 2000))
        self._send_command("osd", width, height, aspect, 2000, 2000)

    def _handle_command_setup(self, wid):
        if self._stream:
            return

        self._wid = wid
        self._ao = self._xine.open_audio_driver()

        self._osd_buffer = shm.create_memory(self._shmkey, 2000 * 2000 * 4 + 16)
        self._osd_buffer.attach()
        self._shmid = shm.getshmid(self._shmkey)

        control_return = []
        self._vo = self._xine.open_video_driver("kaa", control_return = control_return,
                    passthrough = "xv", wid = wid, osd_configure_cb = notifier.WeakCallback(self._osd_configure),
                    osd_buffer = self._osd_buffer.addr + 16, osd_stride = 2000 * 4, osd_rows = 2000,
#        self._vo = self._xine.open_video_driver("xv", wid = wid,
                    frame_output_cb = notifier.WeakCallback(self._x11_frame_output_cb),
                    dest_size_cb = notifier.WeakCallback(self._x11_dest_size_cb))
#        self._vo = self._xine.open_video_driver("none")
        self.driver_control = control_return[0]

        self._stream = self._xine.new_stream(self._ao, self._vo) 
        self._stream.signals["event"].connect_weak(self.handle_xine_event)

        self._noise_post = self._xine.post_init("noise", video_targets = [self._vo])
        self._noise_post.set_parameters(luma_strength = 3, quality = "temporal")
        #self._stream.get_video_source().wire(self._noise_post.get_default_input())

        self._expand_post = self._xine.post_init("expand", video_targets = [self._vo])

        self._deint_post = self._xine.post_init("tvtime", video_targets = [self._expand_post.get_default_input()])
        self._deint_post.set_parameters(method = "GreedyH")#, chroma_filter = True)
        self._stream.get_video_source().wire(self._deint_post.get_default_input())
        xine._debug_show_chain(self._stream._obj)

        #self._driver_control("set_passthrough", False)
        return self._stream


    def _handle_command_open(self, mrl):
        self._stream.open(mrl)
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
        print "EVENT", event.type, event.data
        print self._x11_last_aspect, self.get_stream_info()


    def _handle_command_osd_update(self, alpha, visible, invalid_regions):
        if alpha:
            self.driver_control("set_osd_alpha", alpha)
        if visible:
            self.driver_control("set_osd_visibility", visible)
        if invalid_regions:
            self.driver_control("osd_invalidate_rect", invalid_regions)


    def _handle_command_play(self):
        if self._stream.get_status() == xine.STATUS_PLAY:
            self._stream.set_parameter(xine.PARAM_SPEED, xine.SPEED_NORMAL)
        else:
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
        if self._stream:
            self._stream.stop()
            self._stream.close()
        sys.exit(0)




class XinePlayer(MediaPlayer):

    _instance_count = 0

    def __init__(self):
        super(XinePlayer, self).__init__()
        self._instance_id = "kaaxine-%d-%d" % (os.getpid(), XinePlayer._instance_count)
        XinePlayer._instance_count += 1

        self._shmkey = int(md5.md5(self._instance_id).hexdigest()[:7], 16)
        self._osd_buffer = None
        kaa.signals["shutdown"].connect_weak(self._remove_shmem)

        self._state_data = None
        self._stream_info = {}
        self._position = 0.0

        self._spawn()

    def __del__(self):
        self._remove_shmem()
        kaa.signals["shutdown"].disconnect(self._remove_shmem)

    def _remove_shmem(self):
        if self._osd_buffer:
            try:
                self._osd_buffer.detach()
            except shm.error:
                # Probably already deleted by child
                pass
        

    def _spawn(self):
        # Launch self (-u is unbuffered stdout)
        self._process = notifier.Process("%s -u %s" % (sys.executable, __file__))
        self._process.signals["stdout"].connect_weak(self._handle_line)
        self._process.signals["stderr"].connect_weak(self._handle_line)
        self._process.signals["completed"].connect_weak(self._exited)
        self._process.set_stop_command(self._end_child)
        self._process.start(str(self._shmkey))



    def _send_command(self, command, *args):
        s = repr((command, args))
        self._process.write(s + "\n")


    def _end_child(self):
        self._send_command("die")


    def _exited(self, exitcode):
        self._state = STATE_NOT_RUNNING
        self.signals["end"].emit()


    def _handle_line(self, line):
        if line[0] == "!":
            command, args = eval(line[1:])
            getattr(self, "_handle_command_" + command)(*args)
        else:
            print "CHILD", line


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


    def _handle_command_osd(self, width, height, aspect, buffer_width, buffer_height):
        if not self._osd_buffer:
            shmid = shm.getshmid(self._shmkey)
            if shmid:
                self._osd_buffer = shm.memory(shmid)
                self._osd_buffer.attach()

        self.signals["osd_configure"].emit(width, height, self._osd_buffer.addr + 16, 
                                           buffer_width, buffer_height)
 
            
    def _handle_command_resize(self, size):
        self._window.resize(size)


    def _handle_window_resize_event(self, old_size, new_size):
        self._send_command("window_resized", new_size)
        

    def _handle_command_stream_info(self, info):
        self._stream_info = info
        if self._state == STATE_OPENING:
            self._state = STATE_IDLE
            self.signals["start"].connect_weak_once(self._show_window)
            self.signals["open"].emit()


    def _show_window(self):
        if self._window:
            self._window.show()
            self._send_command("window_resized", self._window.get_size())


    def open(self, mrl):
        if self._window == None:
            # Use the user specified size, or some sensible default.
            win_size = self._size or (640, 480)
            window = display.X11Window(size = win_size, title = "Movie Window")
            self.set_window(window)

        # TODO: no window
        self._send_command("setup", self._window.get_id())

        self._position = 0.0
        self._send_command("open", mrl)
        self._state = STATE_OPENING 
 
    def play(self):
        if self.get_state() == STATE_OPENING:
            self.signals["open"].connect_once(self.play)
            return
        else:
            self._send_command("play")


    def pause(self):
        self._send_command("pause")
        

    def pause_toggle(self):
        if self.get_state() == STATE_PLAYING:
            self.pause()
        else:
            self.play()
        

    def seek_relative(self, offset):
        self._send_command("seek", 0, offset)


    def seek_absolute(self, position):
        self._send_command("seek", 1, position)


    def seek_percentage(self, percent):
        pos = (percent / 100.0) * 65535
        self._send_command("seek", 2, pos)


    def osd_update(self, alpha = None, visible = None, invalid_regions = None):
        self._send_command("osd_update", alpha, visible, invalid_regions)
        

    def osd_can_update(self):
        # FIXME
        return True


    def set_window(self, window):
        super(XinePlayer, self).set_window(window)
        window.signals["resize_event"].disconnect(self._handle_window_resize_event)
        window.signals["resize_event"].connect_weak(self._handle_window_resize_event)


    def get_player_id(self):
        return "xine"


 
def get_capabilities():
    caps = CAP_VIDEO | CAP_AUDIO | CAP_OSD | CAP_CANVAS | CAP_DVD | \
           CAP_DVD_MENUS | CAP_DYNAMIC_FILTERS | CAP_VARIABLE_SPEED | \
           CAP_VISUALIZATION | CAP_DEINTERLACE
    schemes = [ "file", "fifo", "dvd", "vcd", "cdda", "http", "tcp", "udp",
                "rtp", "smb", "mms", "pnm", "rtsp" ]
    return caps, schemes


if __name__ == "__main__":
    # We're being called as a child.
    import gc
    #gc.set_debug(gc.DEBUG_COLLECTABLE | gc.DEBUG_UNCOLLECTABLE | gc.DEBUG_INSTANCES | gc.DEBUG_OBJECTS)
    kaa.base.create_logger()
    player = XinePlayerChild(sys.argv[1])
    kaa.main()
    if player._osd_buffer:
        player._osd_buffer.detach()
        shm.remove_memory(player._shmid)

    # Force garbage collection for testing ...
    del player
    gc.collect()
else:
    register_player("xine", XinePlayer, get_capabilities)

