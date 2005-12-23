__all__ = ['PlayerOSDCanvas', 'Movie' ]

from displays.buffer import BufferCanvas
from displays.x11 import X11Canvas
from image import *
import kaa.player
from kaa import notifier, display, evas, base


class PlayerOSDCanvas(BufferCanvas):

    def __init__(self, player = None, size = (800, 600)):
        super(PlayerOSDCanvas, self).__init__(size)

        self._alpha = self._osd_alpha = 255
        self._osd_visible = 0
        self.hide()
        self._player = None

        if player:
            self.set_player(player)


    def set_player(self, player):
        if self._player:
            self._player.signals["osd_configure"].disconnect(self._osd_configure)
        if player:
            assert(player.has_capability(kaa.player.CAP_OSD))
            player.signals["osd_configure"].connect_weak(self._osd_configure)
        self._player = player


    def _render_queued(self):
        if not self._player or not self._player.osd_can_update():
            return

        return super(PlayerOSDCanvas, self)._render_queued()


    def _render(self):
        regions = super(PlayerOSDCanvas, self)._render()

        self._player.osd_update(self._osd_alpha, self["visible"], regions)


    def _set_property_color(self, color):
        color = self._parse_color(color)
        r, g, b, a = color
        # vf_overlay does not support color filters, only alpha.
        assert(r == g == b == 255)
        # 0 <= alpha < = 255
        a = max(0, min(255, a))
        if hasattr(self, "_osd_alpha") and self._osd_alpha != a:
            # If the alpha set here is different than the vf_overlay alpha,
            # then we need to queue a render.
            self._osd_alpha = a
            self._queue_render()

        # But tell the lower canvas objects we're still fully opaque,
        # otherwise our children will get blended to the new alpha by
        # evas, which is unnecessary since vf_overlay supports global
        # alpha.
        super(PlayerOSDCanvas, self)._set_property_color((255,255,255,255))

    def get_color(self):
        return (255, 255, 255, self._osd_alpha)


    def _osd_configure(self, width, height, buffer, buffer_width, buffer_height):
        if self._o:
            if buffer != self.get_buffer():
                self._reset()
            else:
                self._o.output_size_set((width, height))
                self._queue_render()

        if not self._o:
            self.create((buffer_width, buffer_height), buffer)
            self._o.output_size_set((width, height))



class Movie(Image):

    def __init__(self, mrl = None):
        super(Movie, self).__init__()
        self._supported_sync_properties += ["detached"]
        self._player = None
        self._window = None
        self.osd = None

        self.signals = {
            "pause": notifier.Signal(),
            "play": notifier.Signal(),
            "pause_toggle": notifier.Signal(),
            "seek": notifier.Signal(),
            "open": notifier.Signal(),
            "start": notifier.Signal(),
            # Stream ended (either stopped by user or finished)
            "end": notifier.Signal(),
            "stream_changed": notifier.Signal()
        }

        self["detached"] = False
        self["aspect"] = "preserve"
        self.set_has_alpha(False)
        # Holds the number of frames received at the current frame size
        self._frame_output_size_count = 0
        self.osd = PlayerOSDCanvas()

        if mrl:
            self.open(mrl)

    def open(self, mrl):
        #cls = kaa.player.get_player_class(player = "xine")
        #cls = kaa.player.get_player_class(player = "mplayer")
        cls = kaa.player.get_player_class(mrl = mrl, caps = kaa.player.CAP_CANVAS)
        if not cls:
            raise canvas.CanvasError, "No suitable player found"

        if self._player != None:
            self._player.stop()
            if isinstance(self._player, cls):
                return self._player.open(mrl)

            # Continue open once our current player is dead.  We want to wait
            # before spawning the new one so that it releases the audio 
            # device.
            self._player.signals["quit"].connect_once(self._open, mrl, cls)
            self._player.die()
            return

        self._open(mrl, cls)
        self._aspect = 0.0


    def _open(self, mrl, cls):
        self._player = cls()
        self._player.signals["start"].connect_weak(self._video_start)
        self._player.signals["frame"].connect_weak(self._new_frame)
        self._player.signals["stream_changed"].connect_weak(self._stream_changed)

        for signal in self.signals:
            if signal in self._player.signals:
                self._player.signals[signal].connect_weak(self.signals[signal].emit)

        if self._player.has_capability(kaa.player.CAP_OSD):
            self.osd.set_player(base.weakref(self._player))
            self.osd._queue_render()
        else:
            self.osd.set_player(None)

        self._aspect = None
        self._waiting_for_render = False

        self._create_canvas_subwindow()
        self._force_sync_property("detached")
        self._force_sync_property("visible")
        self._player.open(mrl)


    def play(self):
        if not self._player:
            raise SystemError, "Play called before open"
            return

        if self._open in self._player.signals["quit"]:
            # Waiting for old player to die.
            self.signals["open"].connect_once(self.play)
            return

        self._player.play()


    def _canvased(self, canvas):
        super(Movie, self)._canvased(canvas)

        if not self._player:
            return

        self._create_canvas_subwindow()

    def _video_start(self):
        if not self._window:
            self._window = self._player.get_window()
        if not self["detached"]:
            self._window.hide()
        else:
            self._window.show(raised = True)
            self._window.resize(self.get_canvas().get_size())

    def _create_canvas_subwindow(self):
        canvas = self.get_canvas()
        if not isinstance(canvas, X11Canvas):
            return
        if not isinstance(canvas.get_window(), display.X11Window):
            return

        if not self._window:
            self._window = display.X11Window(size = (320, 200), parent = canvas.get_window())

        self._window.show()
        if not self["detached"]:
            self._window.lower_window()
        self._player.set_window(self._window)


    def detach(self):
        self.set_detached(True)

    def attach(self):
        self.set_detached(False)

    def set_detached(self, detached):
        self["detached"] = detached
 
    def get_detached(self):
        return self["detached"]       

    def _sync_property_detached(self):
        if not self._player:
            return False

        if self["detached"]:
            if not self._window:
                return
            self._player.set_frame_output_mode(vo = True, notify = False)
            self._window.resize(self.get_canvas().get_window().get_size())
            self._window.move((0, 0))
            self._window.show(raised = True)
        else:
            visible = self._get_relative_values("visible")
            alpha = self._get_relative_values("color")[3]
            self._player.set_frame_output_mode(notify = (visible and alpha > 0))
            if self._window:
                self._window.hide()
            self._player.set_frame_output_mode(vo = False)

 
    def _get_aspect_ratio2(self):
        if not self._player:
            return 1.0

        info = self._player.get_info()
        aspect = 0
        if self._aspect:
            aspect = self._aspect
        elif "aspect" in info:
            aspect = info["aspect"]

        if aspect == 0:
            aspect = 1.0

        return aspect
               


    def _set_frame_output_size(self):
        info = self._player.get_info()
        frame_w, frame_h = info["width"], info["height"]
        if 0 in (frame_w, frame_h):
            return

        w, h = self._get_computed_size()
        if 0 in (w,h):
            return

        # Have the player scale the video if the area is smaller.
        if w * h >= frame_w * frame_h:
            w, h = frame_w, frame_h
        w = w & ~1
        h = h & ~1
        #w = max(320, w & ~1)
        #h = max(200, h & ~1)
        self._player.set_frame_output_mode(size = (w, h))


    def _sync_property_visible(self):
        if not self._player:
            return False

        visible = self._get_relative_values("visible")
        self._player.set_frame_output_mode(notify = visible)

        super(Movie, self)._sync_property_visible()


    def _sync_property_color(self):
        if not self._player:
            return False

        alpha = self._get_relative_values("color")[3]
        if alpha <= 0:
            self._player.set_frame_output_mode(notify = False)
        else:
            self._player.set_frame_output_mode(notify = True)

        super(Movie, self)._sync_property_color()


    def _new_frame(self, width, height, aspect, ptr, format):
        if self["color"][3] <= 0 or not self["visible"]:
            return

        if self._aspect != aspect:
            # If our aspect ratio has changed, our size has probably changed,
            # so cause a reflow.
            #self._force_sync_property("size")
            #self._request_reflow(what_changed = "size")
            self.set_aspect(aspect)
            self._aspect = aspect

        if format == "yv12":
            self.import_pixels(ptr, width, height, evas.PIXEL_FORMAT_YUV420P_601)
        else:
            if self._o.size_get() != (width, height):
                self._o.size_set((width, height))
            self.set_data(width, height, ptr)

        # If we receive more than 5 frames of size that is different than
        # the current display size (on the canvas), ask the player to do the
        # scaling for us (to width multiples of 2)
        d_width, d_height = self._get_computed_size()
        d_width, d_height = d_width & ~1, d_height & ~1
        info = self._player.get_info()
        frame_w, frame_h = info["width"], info["height"]
        if (d_width, d_height) != (width, height) and d_width*d_height < frame_w*frame_h:# and \
            #d_width*d_height > 320*200:
            self._frame_output_size_count += 1
            if self._frame_output_size_count >= 5:
                self._set_frame_output_size()
                self._frame_output_size_count = 0

        self._o.pixels_dirty_set()
        self._queue_render()
        self.get_canvas().signals["updated"].disconnect(self._sync)
        self.get_canvas().signals["updated"].connect_once(self._sync)


    def _sync(self, regions):
        self._player.unlock_frame_buffer()

    def _stream_changed(self):
        d_width, d_height = self._get_computed_size()
        if (d_width, d_height) != self._o.size_get():
            self._o.resize((d_width, d_height))
            self._o.fill_set((0, 0), (d_width, d_height))

        self._set_frame_output_size()


    def stop(self):
        if self._player:
            self._player.stop()

    def pause(self):
        if self._player:
            self._player.pause()

    def pause_toggle(self):
        if self._player:
            self._player.pause_toggle()

    def seek_relative(self, offset):
        if self._player:
            self._player.seek_relative(offset)

    def seek_absolute(self, position):
        if self._player:
            self._player.seek_absolute(position)

    def seek_percentage(self, percent):
        if self._player:
            self._player.seek_percent(position)

    def get_position(self):
        if self._player:
            self._player.get_position()

    def get_info(self):
        if self._player:
            self._player.get_info()

    def nav_command(self, input):
        if self._player:
            self._player.nav_command(input)

    def is_in_menu(self):
        if self._player:
            return self._player.is_in_menu()
        return False
