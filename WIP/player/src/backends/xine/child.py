import sys
import md5
import gc

import kaa
import kaa.notifier
import kaa.shm
import kaa.xine as xine

from kaa.config import Group, Var

from kaa.player.utils import Player


# Config group for xine player
config = Group(desc = 'Options for xine player', schema = [
    Group(name = 'deinterlacer', desc = 'Deinterlacer options', schema = [
        Var(name = 'method', default = 'GreedyH',
            desc = 'tvtime method to use, e.g. TomsMoComp, GreedyH, LinearBlend, etc.'),
        Var(name = 'chroma_filter', default = True,
            desc = 'Enable chroma filtering (better quality, higher cpu usage')
    ])
])



BUFFER_UNLOCKED = 0x10
BUFFER_LOCKED = 0x20

class XinePlayerChild(Player):

    def __init__(self, instance_id):
        Player.__init__(self)

        self._xine = xine.Xine()
        self._stream = self._vo = self._ao = None
        self._osd_shmkey = int(md5.md5(instance_id + "osd").hexdigest()[:7], 16)
        self._frame_shmkey = int(md5.md5(instance_id + "frame").hexdigest()[:7], 16)
        self._osd_shmem = self._frame_shmem = None

        self._x11_window_size = 0, 0
        self._x11_last_aspect = -1
        self._status = kaa.notifier.WeakTimer(self._status_output)
        self._status_last = None

        self._xine.set_config_value("effects.goom.fps", 20)
        self._xine.set_config_value("effects.goom.width", 512)
        self._xine.set_config_value("effects.goom.height", 384)
        self._xine.set_config_value("effects.goom.csc_method", "Slow but looks better")


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
            self._status_last = cur_status
            self.parent.set_status(*cur_status)


    def _get_stream_info(self):
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


    # #############################################################################
    # kaa.xine callbacks
    # #############################################################################

    def _x11_frame_output_cb(self, width, height, aspect):
        #print "Frame output", width, height, aspect
        w, h, a = self._xine._get_vo_display_size(width, height, aspect)
        if abs(self._x11_last_aspect - a) > 0.01:
            print "VO: %dx%d -> %dx%d" % (width, height, w, h)
            self.parent.resize((w, h))
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
            self._frame_shmem = kaa.shm.create_memory(self._frame_shmkey, frame_shmem_size)
            self._frame_shmem.attach()
        if not self._osd_shmem:
            self._osd_shmem = kaa.shm.create_memory(self._osd_shmkey, 2000 * 2000 * 4 + 16)
            self._osd_shmem.attach()
            self._osd_shmem.write(chr(BUFFER_UNLOCKED))

        # FIXME: don't hardcode buffer dimensions
        assert(width*height*4 < 2000*2000*4)
        self.parent.osd_configure(width, height, aspect)
        return self._osd_shmem.addr + 16, width * 4, self._frame_shmem.addr


    def handle_xine_event(self, event):
        if len(event.data) > 1:
            del event.data["data"]
        print "EVENT", event.type, event.data
        if event.type == xine.EVENT_UI_CHANNELS_CHANGED:
            self.parent.set_stream_info(True, self._get_stream_info())
        self.parent.xine_event(event.type, event.data)


    # #############################################################################
    # Commands from parent process
    # #############################################################################

    def window_changed(self, wid, size, visible, exposed_regions):
        self._x11_window_size = size
        self._wid = wid
        if self._vo:
            self._vo.send_gui_data(xine.GUI_SEND_VIDEOWIN_VISIBLE, visible)
            self._vo.send_gui_data(xine.GUI_SEND_DRAWABLE_CHANGED, wid)


    def setup(self, wid):
        if self._stream:
            return

        self._wid = wid

        self._ao = self._xine.open_audio_driver()
        control_return = []
        if wid and isinstance(wid, int):
            self._vo = self._xine.open_video_driver(
                "kaa", control_return = control_return,
                passthrough = "xv", wid = wid,
                osd_configure_cb = kaa.notifier.WeakCallback(self._osd_configure),
                # osd_buffer = self._osd_shmem.addr + 16, osd_stride = 2000 * 4,
                # osd_rows = 2000,
                # self._vo = self._xine.open_video_driver("xv", wid = wid,
                frame_output_cb = kaa.notifier.WeakCallback(self._x11_frame_output_cb),
                dest_size_cb = kaa.notifier.WeakCallback(self._x11_dest_size_cb))
            self._driver_control = control_return[0]
        elif wid and isinstance(wid, str) and wid.startswith('fb'):
            self._vo = self._xine.open_video_driver(
                "kaa", control_return = control_return,
                passthrough = "vidixfb",
                osd_configure_cb = kaa.notifier.WeakCallback(self._osd_configure),
                frame_output_cb = kaa.notifier.WeakCallback(self._x11_frame_output_cb),
                dest_size_cb = kaa.notifier.WeakCallback(self._x11_dest_size_cb))
            self._driver_control = control_return[0]
        else:
            self._vo = self._xine.open_video_driver("none")
            self._driver_control = None

        self._stream = self._xine.new_stream(self._ao, self._vo)
        #self._stream.set_parameter(xine.PARAM_VO_CROP_BOTTOM, 10)
        self._stream.signals["event"].connect_weak(self.handle_xine_event)


        # FIXME: plugin stuff should be exposed via api, or configurable
        # somehow.

        #self._noise_post = self._xine.post_init("noise", video_targets = [self._vo])
        #self._noise_post.set_parameters(luma_strength = 3, quality = "temporal")
        #self._stream.get_video_source().wire(self._noise_post.get_default_input())

        #self._deint_post = self._xine.post_init("tvtime", video_targets = [self._expand_post.get_default_input()])
        self._deint_post = self._xine.post_init("tvtime", video_targets = [self._vo])
        self._deint_post.set_parameters(method = config.deinterlacer.method,
                                        chroma_filter = config.deinterlacer.chroma_filter)

        #self._stream.get_video_source().wire(self._deint_post.get_default_input())
        #self._expand_post = self._xine.post_init("expand", video_targets = [self._vo])
        self._expand_post = self._xine.post_init("expand", video_targets = [self._deint_post.get_default_input()])
        self._expand_post.set_parameters(enable_automatic_shift = True)
        self._stream.get_video_source().wire(self._expand_post.get_default_input())

        self._goom_post = None
        if wid:
            self._goom_post = self._xine.post_init("goom", video_targets = [self._vo], audio_targets=[self._ao])

        #self._driver_control("set_passthrough", False)
        return self._stream


    def open(self, mrl):
        try:
            self._stream.open(mrl)
            if not self._stream.get_info(xine.STREAM_INFO_HAS_VIDEO) and self._goom_post:
                self._stream.get_audio_source().wire(self._goom_post.get_default_input())
            else:
                self._stream.get_audio_source().wire(self._ao)
            xine._debug_show_chain(self._stream._obj)
        except xine.XineError:
            self.parent.set_stream_info(False, self._stream.get_error())
            print "Open failed:", self._stream.get_error()
            return
        self.parent.set_stream_info(True, self._get_stream_info())
        self._status.start(0.1)


    def osd_update(self, alpha, visible, invalid_regions):
        if not self._osd_shmem:
            return

        if alpha != None:
            self._driver_control("set_osd_alpha", alpha)
        if visible != None:
            self._driver_control("set_osd_visibility", visible)
        if invalid_regions != None:
            self._driver_control("osd_invalidate_rect", invalid_regions)
        self._osd_shmem.write(chr(BUFFER_UNLOCKED))


    def play(self):
        status = self._stream.get_status()
        if status == xine.STATUS_STOP:
            self._stream.play()


    def pause(self):
        self._stream.set_parameter(xine.PARAM_SPEED, xine.SPEED_PAUSE)


    def resume(self):
        self._stream.set_parameter(xine.PARAM_SPEED, xine.SPEED_NORMAL)


    def seek(self, whence, value):
        if whence == 0:
            self._stream.seek_relative(value)
        elif whence == 1:
            self._stream.seek_absolute(value)
        elif whence == 2:
            self._stream.play(pos = value)


    def stop(self):
        self._status.stop()
        if self._stream:
            self._stream.stop()
            self._stream.close()
        self.parent.play_stopped()


    def die(self):
        self.stop()
        sys.exit(0)
        

    def frame_output(self, vo, notify, size):
        if not self._driver_control:
            # FIXME: Tack, what am I doing here?
            return
        if vo != None:
            self._driver_control("set_passthrough", vo)
        if notify != None:
            if notify:
                print "DEINTERLACE CHEAP MODE: True"
                self._deint_post.set_parameters(cheap_mode = True)
            else:
                print "DEINTERLACE CHEAP MODE: False"
                self._deint_post.set_parameters(cheap_mode = False)

            self._driver_control("set_notify_frame", notify)
        if size != None:
            self._driver_control("set_notify_frame_size", size)


    def input(self, input):
        self._stream.send_event(input)









player = XinePlayerChild(sys.argv[1])
kaa.main()

# Remove shared memory.  We don't detach right away, because the vo
# thread might still be running, and it will crash if it tries to write
# to that memory.
if player._osd_shmem:
    kaa.shm.remove_memory(player._osd_shmem.shmid)
if player._frame_shmem:
    kaa.shm.remove_memory(player._frame_shmem.shmid)

# Force garbage collection for testing.
del player
gc.collect()

sys.exit(0)
