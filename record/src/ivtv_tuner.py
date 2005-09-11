# -*- coding: iso-8859-1 -*-
# -----------------------------------------------------------------------
# ivtv_tuner.py - Python interface to ivtv based capture cards.
# -----------------------------------------------------------------------
# $Id$
#
# Notes: http://ivtv.sf.net
#
# Todo:        
#
# -----------------------------------------------------------------------------
# kaa-record - A recording module
# Copyright (C) 2005 S<F6>nke Schwardt, Dirk Meyer
#
# First Edition: Rob Shortt <rob@tvcentric.com>
# Maintainer:    Rob Shortt <rob@tvcentric.com>
#
# Please see the file doc/CREDITS for a complete list of authors.
#
# -----------------------------------------------------------------------
#
# The contents of this file are originally taken from:
#
#   Freevo - A Home Theater PC framework
#   Copyright (C) 2003-2005 Krister Lagerstrom, Dirk Meyer, et al. 
#   Please see Freevo's doc/CREDITS for a complete list of authors.
#   src/tv/ivtv.py by Rob Shortt <rob@tvcentric.com>
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
# ----------------------------------------------------------------------- */
"""
#define VIDIOC_STREAMOFF    _IOW  ('V', 19, int)
        
static inline int ivtv_api_enc_endgop(int ivtvfd, int gop)
{
        /* Send Stop at end of GOP API */
        if (ioctl(ivtvfd, IVTV_IOC_S_GOP_END, &gop) < 0)
                fprintf(stderr, "ioctl: IVTV_IOC_S_GOP_END failed\n");
        return 0;
}       
        
static inline int ivtv_api_enc_stop(int ivtvfd)
{               
        int dummy = 0;
        /* Send Stop Capture API */
        if (ioctl(ivtvfd, VIDIOC_STREAMOFF, &dummy) < 0)
                fprintf(stderr, "ioctl: VIDIOC_STREAMOFF failed\n");
        return 0;
}
"""

# python imports
import logging
import string
import struct
import time

# kaa imports
from kaa.base.ioctl import ioctl, IOR, IOW, IOWR
from v4l_tuner import V4L

log = logging.getLogger('record')


# Stream types 
IVTV_STREAM_PS     =  0
IVTV_STREAM_TS     =  1
IVTV_STREAM_MPEG1  =  2
IVTV_STREAM_PES_AV =  3
IVTV_STREAM_PES_V  =  5
IVTV_STREAM_PES_A  =  7
IVTV_STREAM_DVD    = 10
IVTV_STREAM_VCD    = 11
IVTV_STREAM_SVCD   = 12
IVTV_STREAM_DVD_S1 = 13
IVTV_STREAM_DVD_S2 = 14


# structs and ioctls

VIDIOC_STREAMOFF = IOW('V', 19, 'i')
CODEC_ST = '15I'
IVTV_IOC_G_CODEC = IOR('@', 48, CODEC_ST)
IVTV_IOC_S_CODEC = IOW('@', 49, CODEC_ST)
IVTV_IOC_S_GOP_END = IOWR('@', 50, 'i')

MSP_MATRIX_ST = '2i'
IVTV_IOC_S_MSP_MATRIX = IOW('@', 210, MSP_MATRIX_ST)


class IVTV(V4L):

    def __init__(self, device, norm, chanlist=None, card_input=4,
                 custom_frequencies=None, resolution=None, aspect=2,
                 audio_bitmask=None, bframes=None, bitrate_mode=1,
                 bitrate=4500000, bitrate_peak=4500000, dnr_mode=None,
                 dnr_spatial=None, dnr_temporal=None, dnr_type=None, framerate=None,
                 framespergop=None, gop_closure=1, pulldown=None, stream_type=14):
        """
        Notes:
            my old defaults for NTSC, some of these are set automaticly 
            by the driver

            self.input = 4
            self.resolution = '720x480'
            self.aspect = 2
            self.audio_bitmask = 0x00a9
            self.bframes = 3
            self.bitrate_mode = 1
            self.bitrate = 4500000
            self.bitrate_peak = 4500000
            self.dnr_mode = 0
            self.dnr_spatial = 0
            self.dnr_temporal = 0
            self.dnr_type = 0
            self.framerate = 0
            self.framespergop = 15
            self.gop_closure = 1
            self.pulldown = 0
            self.stream_type = 14
        """
        V4L.__init__(self, device, norm, chanlist, card_input, custom_frequencies)

        self.resolution = resolution
        self.aspect = aspect
        self.audio_bitmask = audio_bitmask
        self.bframes = bframes
        self.bitrate_mode = bitrate_mode
        self.bitrate = bitrate
        self.bitrate_peak = bitrate_peak
        self.dnr_mode = dnr_mode
        self.dnr_spatial = dnr_spatial
        self.dnr_temporal = dnr_temporal
        self.dnr_type = dnr_type
        self.framerate = framerate
        self.framespergop = framespergop
        self.gop_closure = gop_closure
        self.pulldown = pulldown
        self.stream_type = stream_type


        if self.norm == 'NTSC':
            # special defaults for NTSC

            if not self.resolution:
                self.resolution = "740x480"

        elif self.norm == 'PAL':
            # special defaults for PAL

            if not self.resolution:
                self.resolution = "720x576"

        else:  
            # special defaults for SECAM

            if not self.resolution:
                self.resolution = "720x576"


        (width, height) = string.split(self.resolution, 'x')
        self.setfmt(int(width), int(height))

        codec = self.getCodecInfo()

        for a in [ 'aspect', 'audio_bitmask', 'bframes', 'bitrate_mode', 'bitrate', 
                   'bitrate_peak', 'dnr_mode', 'dnr_spatial', 'dnr_temporal',
                   'dnr_type', 'framerate', 'framespergop', 'gop_closure', 'pulldown',
                   'stream_type' ]:

            if not hasattr(codec, a):
                log.error('IVTV codec has no "%s" option' % a)
                continue

            b = getattr(self, a, None)
            c = getattr(codec, a)

            if b is not None:
                # set codec based on self
                setattr(codec, a, b)
            else:
                # set self based on codec
                setattr(self, a, c)

        self.setCodecInfo(codec)


    def setCodecInfo(self, codec):
        val = struct.pack( CODEC_ST, 
                           codec.aspect,
                           codec.audio_bitmask,
                           codec.bframes,
                           codec.bitrate_mode,
                           codec.bitrate,
                           codec.bitrate_peak,
                           codec.dnr_mode,
                           codec.dnr_spatial,
                           codec.dnr_temporal,
                           codec.dnr_type,
                           codec.framerate,
                           codec.framespergop,
                           codec.gop_closure,
                           codec.pulldown,
                           codec.stream_type)
        r = ioctl(self.devfd, IVTV_IOC_S_CODEC, val)


    def getCodecInfo(self):
        val = struct.pack( CODEC_ST, 0,0,0,0,0,0,0,0,0,0,0,0,0,0,0 )
        r = ioctl(self.devfd, IVTV_IOC_G_CODEC, val)
        codec_list = struct.unpack(CODEC_ST, r)
        return IVTVCodec(codec_list)


    def mspSetMatrix(self, input=None, output=None):
        if not input: input = 3
        if not output: output = 1

        val = struct.pack(MSP_MATRIX_ST, input, output)
        r = ioctl(self.devfd, IVTV_IOC_S_MSP_MATRIX, val)


    def print_settings(self):
        V4L.print_settings(self)

        codec = self.getCodecInfo()

        log.info('CODEC::aspect: %s' % codec.aspect)
        log.info('CODEC::audio_bitmask: %s' % codec.audio_bitmask)
        log.info('CODEC::bfrmes: %s' % codec.bframes)
        log.info('CODEC::bitrate_mode: %s' % codec.bitrate_mode)
        log.info('CODEC::bitrate: %s' % codec.bitrate)
        log.info('CODEC::bitrate_peak: %s' % codec.bitrate_peak)
        log.info('CODEC::dnr_mode: %s' % codec.dnr_mode)
        log.info('CODEC::dnr_spatial: %s' % codec.dnr_spatial)
        log.info('CODEC::dnr_temporal: %s' % codec.dnr_temporal)
        log.info('CODEC::dnr_type: %s' % codec.dnr_type)
        log.info('CODEC::framerate: %s' % codec.framerate)
        log.info('CODEC::framespergop: %s' % codec.framespergop)
        log.info('CODEC::gop_closure: %s' % codec.gop_closure)
        log.info('CODEC::pulldown: %s' % codec.pulldown)
        log.info('CODEC::stream_type: %s' % codec.stream_type)


class IVTVCodec(object):
    def __init__(self, args):
        self.aspect        = args[0]
        self.audio_bitmask = args[1]
        self.bframes       = args[2]
        self.bitrate_mode  = args[3]
        self.bitrate       = args[4]
        self.bitrate_peak  = args[5]
        self.dnr_mode      = args[6]
        self.dnr_spatial   = args[7]
        self.dnr_temporal  = args[8]
        self.dnr_type      = args[9]
        self.framerate     = args[10]
        self.framespergop  = args[11]
        self.gop_closure   = args[12]
        self.pulldown      = args[13]
        self.stream_type   = args[14]


