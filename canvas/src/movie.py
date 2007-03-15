# -*- coding: iso-8859-1 -*-
# -----------------------------------------------------------------------------
# $Id$
# -----------------------------------------------------------------------------
# kaa.canvas - Canvas library based on kaa.evas
# Copyright (C) 2005, 2006 Jason Tackaberry
#
# First Edition: Jason Tackaberry <tack@sault.org>
# Maintainer:    Jason Tackaberry <tack@sault.org>
#
# Please see the file AUTHORS for a complete list of authors.
#
# This library is free software; you can redistribute it and/or modify
# it under the terms of the GNU Lesser General Public License version
# 2.1 as published by the Free Software Foundation.
#
# This library is distributed in the hope that it will be useful, but
# WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
# Lesser General Public License for more details.
#
# You should have received a copy of the GNU Lesser General Public
# License along with this library; if not, write to the Free Software
# Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA
# 02110-1301 USA
#
# -----------------------------------------------------------------------------

__all__ = ['PlayerOSDCanvas', 'Movie', 'SEEK_RELATIVE', 'SEEK_ABSOLUTE', 'SEEK_PERCENTAGE' ]

from displays.buffer import BufferCanvas
from displays.x11 import X11Canvas
from image import *
import kaa.popcorn
from kaa import notifier, display, evas, weakref
from kaa.popcorn import SEEK_RELATIVE, SEEK_ABSOLUTE, SEEK_PERCENTAGE


class PlayerOSDCanvas(BufferCanvas):

    def __init__(self, player = None, size = (640, 480)):
        self._player = None

        super(PlayerOSDCanvas, self).__init__(size)
        self.hide()

        if player:
            self.set_player(player)


    def set_player(self, player):
        if self._player:
            self._player.signals["osd_configure"].disconnect(self._osd_configure)
        if player:
            assert(player.has_capability(kaa.popcorn.CAP_OSD))
            player.signals["osd_configure"].connect_weak(self._osd_configure)
        self._player = player


    def _render_queued(self):
        if not self._player or not self._player.osd_can_update():
            return

        return super(PlayerOSDCanvas, self)._render_queued()


    def _render(self):
        regions = super(PlayerOSDCanvas, self)._render()
        self._player.osd_update(self['color'][3], self['visible'], regions)

    def _get_relative_values(self, prop, child_asking = None):
        # Override color and visibility for relative values of children;
        # opacity and visiblity are handled by overlay, so canvas does not
        # need to be rerendered for those properties.  (Color filters not
        # supported though.)
        if prop == 'color':
            return 255, 255, 255, 255
        elif prop == 'visible':
            return True
        return super(PlayerOSDCanvas, self)._get_relative_values(prop, child_asking)


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

        self.resize(width, height)



class Movie(Image):

    def __init__(self, mrl = None):
        super(Movie, self).__init__()
        self._supported_sync_properties += ["detached"]
        self._player = kaa.popcorn.Player()
        self._player.signals["start"].connect_weak(self._video_start)
        self._player.signals["frame"].connect_weak(self._new_frame)
        self._player.signals["stream_changed"].connect_weak(self._stream_changed)

        self._window = None
        self._last_format = None
        self.osd = None

        self.signals.update({
            "pause": notifier.Signal(),
            "play": notifier.Signal(),
            "pause_toggle": notifier.Signal(),
            "seek": notifier.Signal(),
            "open": notifier.Signal(),
            "start": notifier.Signal(),
            # Stream ended (either stopped by user or finished)
            "end": notifier.Signal(),
            "stream_changed": notifier.Signal()
        })

        for signal in self.signals:
            if signal in self._player.signals:
                self._player.signals[signal].connect_weak(self.signals[signal].emit)
        self["detached"] = False
        self.set_has_alpha(False)

        # Holds the number of frames received at the saved frame size
        self._frame_output_size_count = 0
        self._frame_output_size = (0, 0)
        self.osd = PlayerOSDCanvas()

        if mrl:
            self.open(mrl)

    def open(self, mrl):
        self._player.stop()
        self._open(mrl)
        self._aspect = 0.0


    def _open(self, mrl):

        if self._player.has_capability(kaa.popcorn.CAP_OSD):
            self.osd.set_player(weakref.weakref(self._player))
            self.osd._queue_render()
        else:
            self.osd.set_player(None)

        self._aspect = None
        self._waiting_for_render = False

        self._create_canvas_subwindow()
        self._force_sync_property("detached")
        self._force_sync_property("visible")
        self._player.open(mrl, caps = kaa.popcorn.CAP_CANVAS)


    def play(self):
        self._player.play()


    def _canvased(self, canvas):
        super(Movie, self)._canvased(canvas)

        if not self._player:
            return

        self._create_canvas_subwindow()

    def _video_start(self):
        if not self._window:
            self._window = self._player.get_window()
            if not self._window:
                return
        if not self["detached"]:
            self._window.lower_window()
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
            self._window = display.X11Window(size = canvas.get_window().get_size(), parent = canvas.get_window())
            self._window.set_cursor_hide_timeout(1)

        self._window.show(raised = True)
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
                self._window.lower_window()
            self._player.set_frame_output_mode(vo = False)


    def _compute_size(self, size, child_asking, extents = None):
        # Intercept computed size and round to nearest multiple of 2.
        fsize = self.get_image_size()
        osize = super(Movie, self)._compute_size(size, child_asking, extents)
        osize = osize[0] & ~1, osize[1] & ~1
        # If the frame size is within a tolerance of 4 pixels in both 
        # dimensions from the computed size, just reuse the frame size.
        if abs(osize[0] - fsize[0]) <= 4 and abs(osize[1] - fsize[1]) <= 4:
            return fsize
        return osize


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
            self.set_aspect(aspect)
            self._aspect = aspect

        if format == "yv12":
            if self._last_format != 'yv12':
                self._o.data_set(0, False)
            self.import_pixels(ptr, width, height, evas.PIXEL_FORMAT_YUV420P_601)
        else:
            self.set_data(width, height, ptr)
            self.set_dirty()

        # If we receive more than 5 frames of a certain size, ask the player
        # to do the scaling for us (to width multiples of 2)
        d_width, d_height = self._get_computed_size()
        info = self._player.get_info()
        frame_w, frame_h = info["width"], info["height"]
        if (d_width, d_height) != (width, height) and d_width*d_height < frame_w*frame_h:# and \
            #d_width*d_height > 320*200:
            if self._frame_output_size == (d_width, d_height):
                self._frame_output_size_count += 1
            else:
                self._frame_output_size = (d_width, d_height)
                self._frame_output_size_count = 0

            if self._frame_output_size_count >= 5:
                self._set_frame_output_size()
                self._frame_output_size_count = 0

        self.get_canvas().signals["updated"].disconnect(self._sync)
        self.get_canvas().signals["updated"].connect_once(self._sync)
        self._last_format = format


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

    def seek(self, value, type = SEEK_RELATIVE):
        if self._player:
            self._player.seek(value, type)

    def get_position(self):
        if self._player:
            return self._player.get_position()
        return 0.0

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
