# -*- coding: iso-8859-1 -*-
# -----------------------------------------------------------------------------
# xine/child.py - xine backend
# -----------------------------------------------------------------------------
# $Id$
#
# -----------------------------------------------------------------------------
# kaa.popcorn - Generic Player API
# Copyright (C) 2006 Jason Tackaberry, Dirk Meyer
#
# Please see the file AUTHORS for a complete list of authors.
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful, but
# WITHOUT ANY WARRANTY; without even the implied warranty of MER-
# CHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the GNU General
# Public License for more details.
#
# You should have received a copy of the GNU General Public License along
# with this program; if not, write to the Free Software Foundation, Inc.,
# 59 Temple Place, Suite 330, Boston, MA 02111-1307 USA
#
# -----------------------------------------------------------------------------

# python imports
import sys
import logging

# kaa imports
import kaa
import kaa.notifier
import kaa.shm
import kaa.xine as xine

# kaa.popcorn imports
from kaa.popcorn.utils import Player
from kaa.popcorn.ptypes import *

from filter import FilterChain

# get and configure logging object
log = logging.getLogger('xine')
log.setLevel(logging.DEBUG)


BUFFER_UNLOCKED = 0x10
BUFFER_LOCKED = 0x20

class XinePlayerChild(Player):

    def __init__(self, osd_shmkey, frame_shmkey):
        Player.__init__(self)

        self._xine = xine.Xine()
        self._vfilter = FilterChain(self._xine)
        self._stream = self._vo = self._ao = None
        self._osd_shmkey = int(osd_shmkey)
        self._frame_shmkey = int(frame_shmkey)
        self._osd_shmem = self._frame_shmem = None

        self._window_size = 0, 0
        self._window_aspect = -1
        self._status = kaa.notifier.WeakTimer(self._status_output)
        self._status_last = None

        self._xine.set_config_value("effects.goom.fps", 20)
        self._xine.set_config_value("effects.goom.width", 512)
        self._xine.set_config_value("effects.goom.height", 384)
        self._xine.set_config_value("effects.goom.csc_method", "Slow but looks better")


    # #########################################################################
    # Stream information utils
    # #########################################################################

    def _status_output(self):
        """
        Outputs stream status information.
        """
        if not self._stream:
            return

        # FIXME: this gets not updated very often, I have no idea why
        t = self._stream.get_pos_length()
        status = self._stream.get_status()
        if status == xine.STATUS_PLAY and None in t:
            # Status is playing, but pos/time is not known for stream,
            # which likely means we have seeked and are not done seeking
            # get, so position is not yet determined.  In this case, don't
            # send a status update to parent yet.
            return

        speed = self._stream.get_parameter(xine.PARAM_SPEED)

        # Line format: pos time length status speed
        # Where status is one of XINE_STATUS_ constants, and speed
        # is one of XINE_SPEED constants.
        cur_status = (t[0], t[1], t[2], status, speed)
        if cur_status != self._status_last:
            self._status_last = cur_status
            self.parent.set_status(*cur_status)


    def _get_streaminfo(self):
        """
        Get information about the current stream.
        """
        if not self._stream:
            return {}

        info = {
            "vfourcc": self._stream.get_info(xine.STREAM_INFO_VIDEO_FOURCC),
            "afourcc": self._stream.get_info(xine.STREAM_INFO_AUDIO_FOURCC),
            "vcodec":  self._stream.get_meta_info(xine.META_INFO_VIDEOCODEC),
            "acodec":  self._stream.get_meta_info(xine.META_INFO_AUDIOCODEC),
            "width":   self._stream.get_info(xine.STREAM_INFO_VIDEO_WIDTH),
            "height":  self._stream.get_info(xine.STREAM_INFO_VIDEO_HEIGHT),
            "aspect":  self._stream.get_info(xine.STREAM_INFO_VIDEO_RATIO) / 10000.0,
            "fps":     self._stream.get_info(xine.STREAM_INFO_FRAME_DURATION),
            "length":  self._stream.get_length(),
        }

        if self._window_aspect != -1:
            # Use the aspect ratio as given to the frame output callback
            # as it tends to be more reliable (particularly for DVDs).
            info["aspect"] = self._window_aspect
        if info["aspect"] == 0 and info["height"] > 0:
            info["aspect"] = info["width"] / float(info["height"])
        if info["fps"]:
            info["fps"] = 90000.0 / info["fps"]
        return info


    # #########################################################################
    # kaa.xine callbacks
    # #########################################################################

    def _xine_frame_output_cb(self, width, height, aspect):
        """
        Return the frame output position and dimensions
        """
        # FIXME: this is called for every frame. So for every frame we jump
        # from C to Python, call _get_vo_display_size in C again and
        # continue in Python. I guess it would be a major speed improvement
        # if this function is directly in C and we only provide the
        # basic information (size, maybe aspect) when it changes.
        w, h, a = self._xine._get_vo_display_size(width, height, aspect)
        if abs(self._window_aspect - a) > 0.01:
            log.debug('VO: %dx%d -> %dx%d', width, height, w, h)
            self.parent.resize((w, h))
            self._window_aspect = a
        if self._window_size != (0, 0):
            w, h = self._window_size
        return (0, 0), (0, 0), (w, h), 1.0


    def _xine_dest_size_cb(self, width, height, aspect):
        """
        Return the output size and aspect.
        """
        w, h = self._window_size
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


    def _handle_xine_event(self, event):
        """
        Received event from xine.
        """
        if len(event.data) > 1:
            del event.data["data"]
        if event.type == xine.EVENT_UI_CHANNELS_CHANGED:
            self.parent.set_streaminfo(True, self._get_streaminfo())
        elif event.type == xine.EVENT_UI_MESSAGE and \
                 event.data['type'] == xine.MSG_AUDIO_OUT_UNAVAILABLE:
            # Failed to open audio driver (async), so create dummy driver and
            # wire stream to that.
            self._ao = self._xine.open_audio_driver("none")
            if self._stream:
                self._stream.get_audio_source().wire(self._ao)
        self.parent.xine_event(event.type, event.data)


    # #############################################################################
    # Commands from parent process
    # #############################################################################

    def window_changed(self, wid, size, visible, exposed_regions):
        """
        Window changed or exposed regions.
        """
        if not self._vo:
            return
        if size is not None:
            self._window_size = size
        if visible is not None:
            self._vo.send_gui_data(xine.GUI_SEND_VIDEOWIN_VISIBLE, visible)
        self._vo.send_gui_data(xine.GUI_SEND_DRAWABLE_CHANGED, wid)


    def configure_video(self, wid, size, aspect):
        """
        Configure video output.
        """
        control_return = []
        self._vo_visible = True
        if size is not None:
            self._window_size = size
        if wid and isinstance(wid, (int, long)):
            self._vo = self._xine.open_video_driver(
                "kaa", control_return = control_return,
                passthrough = "xv", wid = wid,
                osd_configure_cb = kaa.notifier.WeakCallback(self._osd_configure),
                frame_output_cb = kaa.notifier.WeakCallback(self._xine_frame_output_cb),
                dest_size_cb = kaa.notifier.WeakCallback(self._xine_dest_size_cb),
                vsync = self.config.xine.vsync)
            self._driver_control = control_return[0]

        elif wid and isinstance(wid, str) and wid.startswith('fb'):
            self._vo = self._xine.open_video_driver(
                "kaa", control_return = control_return,
                passthrough = "vidixfb",
                osd_configure_cb = kaa.notifier.WeakCallback(self._osd_configure),
                frame_output_cb = kaa.notifier.WeakCallback(self._xine_frame_output_cb),
                dest_size_cb = kaa.notifier.WeakCallback(self._xine_dest_size_cb))
            self._driver_control = control_return[0]

        else:
            self._vo = self._xine.open_video_driver("none")
            self._driver_control = None
            self._vo_visible = False

        # Set new vo on filter chain and configure filters.
        self._vfilter.set_vo(self._vo)
        f = self._vfilter.get("tvtime")
        f.set_parameters(method = self.config.xine.deinterlacer.method,
                         chroma_filter = self.config.xine.deinterlacer.chroma_filter)

        f = self._vfilter.get("expand")
        if aspect:
            aspect, fullscreen = aspect
            # FIXME: is this correct? What about the fullscreen size?
            f.set_parameters(aspect=float(aspect[0])/aspect[1])
        f.set_parameters(enable_automatic_shift = True)

        if self._driver_control:
            self._driver_control("set_passthrough", False)


    def configure_audio(self, driver):
        """
        Configure audio output.
        """
        try:
            self._ao = self._xine.open_audio_driver(driver=driver)
        except xine.XineError:
            # Audio driver initialization failed; initialize a dummy driver
            # instead.
            self._ao = self._xine.open_audio_driver("none")
            return

        if driver == 'alsa':
            set = self._xine.set_config_value
            dev = self.config.audio.device
            if dev.mono:
                set('audio.device.alsa_default_device', dev.mono)
            if dev.stereo:
                set('audio.device.alsa_front_device', dev.stereo)
            if dev.surround40:
                set('audio.device.alsa_surround40_device', dev.surround40)
            if dev.surround51:
                set('audio.device.alsa_surround51_device', dev.surround51)
            if dev.passthrough:
                set('audio.device.alsa_passthrough_device', dev.passthrough)
            if self.config.audio.passthrough:
                set('audio.output.speaker_arrangement', 'Pass Through')
            else:
                channels = { 2: 'Stereo 2.0', 4: 'Surround 4.0', 6: 'Surround 5.1' }
                num = self.config.audio.channels
                set('audio.output.speaker_arrangement', channels[num])

        if self._stream:
            self._stream.get_audio_source().wire(self._ao)


    def configure_stream(self, properties):
        """
        Basic stream setup.
        """
        self._stream = self._xine.new_stream(self._ao, self._vo)
        #self._stream.set_parameter(xine.PARAM_VO_CROP_BOTTOM, 10)
        self._stream.signals["event"].connect_weak(self._handle_xine_event)

        # self._noise_post = self._xine.post_init("noise", video_targets = [self._vo])
        # self._noise_post.set_parameters(luma_strength = 3, quality = "temporal")
        # self._stream.get_video_source().wire(self._noise_post.get_default_input())

        if not self._vo:
            return

        # wire video stream with needed filter
        chain = []
        if properties.get('deinterlace') in (True, 'auto'):
            chain.append('tvtime')
        if properties.get('postprocessing'):
            chain.append('pp')
        chain.append('expand')
        self._vfilter.wire(self._stream.get_video_source(), *chain)



    def open(self, mrl):
        """
        Open mrl to play.
        """
        try:
            self._stream.open(mrl)
            if not self._stream.get_info(xine.STREAM_INFO_HAS_VIDEO)\
                   and self._vo_visible:
                self._goom_post = self._xine.post_init(
                    "goom", video_targets = [self._vo], audio_targets=[self._ao])
                self._stream.get_audio_source().wire(self._goom_post.get_default_input())
            else:
                self._goom_post = None
                self._stream.get_audio_source().wire(self._ao)
        except xine.XineError:
            self.parent.set_streaminfo(False, self._stream.get_error())
            log.error('Open failed: %s', self._stream.get_error())
            return False

        # Check if stream is ok.
        v_unhandled = self._stream.get_info(xine.STREAM_INFO_HAS_VIDEO) and \
            not self._stream.get_info(xine.STREAM_INFO_IGNORE_VIDEO) and \
            not self._stream.get_info(xine.STREAM_INFO_VIDEO_HANDLED)
        a_unhandled = self._stream.get_info(xine.STREAM_INFO_HAS_AUDIO) and \
            not self._stream.get_info(xine.STREAM_INFO_IGNORE_AUDIO) and \
            not self._stream.get_info(xine.STREAM_INFO_AUDIO_HANDLED)

        if v_unhandled or a_unhandled:
            self.parent.set_streaminfo(False, None)
            log.error('unable to play stream')
            return False
        self.parent.set_streaminfo(True, self._get_streaminfo())
        self._status.start(0.03)
        return True


    def osd_update(self, alpha, visible, invalid_regions):
        """
        Update OSD.
        """
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
        """
        Start playback.
        """
        status = self._stream.get_status()
        if status == xine.STATUS_STOP:
            self._stream.play()
            xine._debug_show_chain(self._stream._obj)


    def pause(self):
        """
        Pause playback.
        """
        self._stream.set_parameter(xine.PARAM_SPEED, xine.SPEED_PAUSE)


    def resume(self):
        """
        Resume playback.
        """
        self._stream.set_parameter(xine.PARAM_SPEED, xine.SPEED_NORMAL)


    def seek(self, value, type):
        """
        Seek in stream.
        """
        if type == SEEK_RELATIVE:
            self._stream.seek_relative(value)
        if type == SEEK_ABSOLUTE:
            self._stream.seek_absolute(value)
        if type == SEEK_PERCENTAGE:
            self._stream.play(pos = (value / 100.0) * 65535)


    def stop(self):
        """
        Stop playback.
        """
        self._status.stop()
        if self._stream:
            self._stream.stop()
            self._stream.close()
        self.parent.play_stopped()


    def die(self):
        """
        Stop process.
        """
        self.stop()
        sys.exit(0)


    def set_audio_delay(self, delay):
        """
        Set audio delay.
        """
        # xine-lib wants units in 1/90000 sec, so convert.
        delay = -int(delay * 90000.0)
        self._stream.set_parameter(xine.PARAM_AV_OFFSET, delay)


    def set_frame_output_mode(self, vo, notify, size):
        """
        Set frame output mode.
        """
        if not self._driver_control:
            # If vo driver used isn't kaa (which may not be for testing/
            # debugging purposes) then _driver_control won't be set.
            # This could also happen if there is no vo set (i.e. audio only).
            # In either case, there's nothing to do.
            return

        if vo != None:
            self._driver_control("set_passthrough", vo)
        if notify != None:
            set_parameters = self._vfilter.get('tvtime').set_parameters
            if notify:
                log.info('deinterlace cheap mode: True')
                set_parameters(cheap_mode = True, framerate_mode = 'half_top')
            else:
                log.info('deinterlace cheap mode: False')
                set_parameters(cheap_mode = False, framerate_mode = 'full')

            self._driver_control("set_notify_frame", notify)
        if size != None:
            self._driver_control("set_notify_frame_size", size)


    def input(self, input):
        """
        Send input (e.g. DVD navigation)
        """
        self._stream.send_event(input)


    def set_property(self, prop, value):
        """
        Set a property to a new value.
        """
        current = self._vfilter.get_chain()
        chain = []
        if prop == 'deinterlace':
            if value:
                chain.append('tvtime')
        elif 'tvtime' in current:
            chain.append('tvtime')

        if prop == 'postprocessing':
            if value:
                chain.append('pp')
        elif 'pp' in current:
            chain.append('pp')

        chain.append('expand')
        self._vfilter.rewire(*chain)
