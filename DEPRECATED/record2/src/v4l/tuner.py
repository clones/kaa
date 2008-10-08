# -*- coding: iso-8859-1 -*-
# -----------------------------------------------------------------------------
# tuner.py - v4l(2) python interface
# -----------------------------------------------------------------------------
# $Id$
#
# -----------------------------------------------------------------------------
# kaa-record - A recording module
# Copyright (C) 2007 Sönke Schwardt, Dirk Meyer
#
# First Edition: Dirk Meyer <dmeyer@tzi.de>
# Maintainer:    Dirk Meyer <dmeyer@tzi.de>
#
# The contents of this file are originally taken from Freevo and written by
# Thomas Schueppel <stain@cs.tu-berlin.de> and Rob Shortt <rob@tvcentric.com>
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
import logging
import os
import string
import struct
import sys
from types import *

# kaa imports
import kaa.ioctl as ioctl

log = logging.getLogger('record')


# v4l2 tuner cap types
V4L2_TUNER_CAP_LOW    = 0x0001
V4L2_TUNER_CAP_NORM   = 0x0002
V4L2_TUNER_CAP_STEREO = 0x0010
V4L2_TUNER_CAP_LANG2  = 0x0020
V4L2_TUNER_CAP_SAP    = 0x0020
V4L2_TUNER_CAP_LANG1  = 0x0040

# v4l2 buffer types
V4L2_BUF_TYPE_VIDEO_CAPTURE = 1


# ioctl structs and numbers

FREQUENCY_ST = "III32x"
GETFREQ_NO   = ioctl.IOWR('V', 56, FREQUENCY_ST)
SETFREQ_NO   = ioctl.IOW('V', 57, FREQUENCY_ST)

SETFREQ_NO_V4L = ioctl.IOW('v', 15, "L")

QUERYCAP_ST  = "16s32s32sLL16x"
QUERYCAP_NO  = ioctl.IOR('V',  0, QUERYCAP_ST)

ENUMSTD_ST   = "LQ24s2LL16x"
ENUMSTD_NO   = ioctl.IOWR('V', 25, ENUMSTD_ST)

STANDARD_ST  = "Q"
GETSTD_NO    = ioctl.IOR('V', 23, STANDARD_ST)
SETSTD_NO    = ioctl.IOW('V', 24, STANDARD_ST)

ENUMINPUT_ST = "L32sLLLQL16x"
ENUMINPUT_NO = ioctl.IOWR('V', 26, ENUMINPUT_ST)

INPUT_ST  = "L";
GETINPUT_NO  = ioctl.IOR('V', 38, INPUT_ST)
SETINPUT_NO  = ioctl.IOWR('V', 39, INPUT_ST)

FMT_ST = "L7L4x168x"
GET_FMT_NO = ioctl.IOWR ('V',  4, FMT_ST)
SET_FMT_NO = ioctl.IOWR ('V',  5, FMT_ST)

FMT_VBI_ST = "12L00x"
FMT_VBI_VARS = ('type', 'sampling_rate', 'offset', 'samples_per_line', 'sample_format',
                'start0', 'start1', 'count0', 'count1', 'flags', 'reserved0', 'reserved1')
GET_FMT_VBI_NO = ioctl.IOWR ('V',  4, FMT_VBI_ST)
SET_FMT_VBI_NO = ioctl.IOWR ('V',  5, FMT_VBI_ST)

# struct v4l2_tuner
TUNER_ST = "L32si5L2l16x"
TUNER_VARS = ('index', 'name', 'type', 'capabilities', 'rangelow', 'rangehigh',
              'rxsubchans', 'audmode', 'signal', 'afc')
GET_TUNER_NO = ioctl.IOWR ('V', 29, TUNER_ST)
SET_TUNER_NO = ioctl.IOW  ('V', 30, TUNER_ST)

AUDIO_ST = "L32sLL8x"
GET_AUDIO_NO = ioctl.IOWR ('V', 33, AUDIO_ST)
SET_AUDIO_NO = ioctl.IOW  ('V', 34, AUDIO_ST)

VIDIOC_STREAMON_ST = 'i'
VIDIOC_STREAMOFF_ST = 'i'
VIDIOC_STREAMON  = ioctl.IOW('V', 18, VIDIOC_STREAMON_ST)
VIDIOC_STREAMOFF = ioctl.IOW('V', 19, VIDIOC_STREAMOFF_ST)


NORMS = { 'NTSC'  : 0x3000,
          'PAL'   : 0xff,
          'SECAM' : 0x7f0000  }


def unpack_dict(frm, var, r):
    r = struct.unpack( frm, r )
    assert(len(r) == len(var))
    d = {}
    for i, v in enumerate(var):
        d[v] = r[i]
    return d


def pack_dict(frm, var, d):
    l = []
    for v in var:
        l.append(d[v])
    return struct.pack(frm, *l)


class Tuner(object):

    def __init__(self, device, norm, card_input=1):
        """
        """
        if not type(norm) is StringType or norm.upper() not in NORMS.keys():
            log.error('bad norm "%s", using NTSC as default' % norm)
            norm = 'NTSC'

        self.devfd = os.open(device, os.O_RDONLY | os.O_NONBLOCK)
        if self.devfd < 0:
            raise RuntimeError('failed to open %s' % device)

        cardcaps          = self.querycap()
        self.driver       = cardcaps[0][:cardcaps[0].find('\0')]
        self.card         = cardcaps[1][:cardcaps[1].find('\0')]
        self.bus_info     = cardcaps[2]
        self.version      = cardcaps[3]
        self.capabilities = cardcaps[4]

        self.setstd(NORMS.get(norm.upper()))
        self.setinput(card_input)

        # XXX TODO: make a good way of setting the capture resolution
        # self.setfmt(int(width), int(height))


    def getfreq(self):
        val = struct.pack( FREQUENCY_ST, 0,0,0 )
        try:
            r = ioctl.ioctl(self.devfd, GETFREQ_NO, val)
            (junk,junk, freq, ) = struct.unpack(FREQUENCY_ST, r)
            return freq
        except IOError:
            log.warn('Failed to get frequency, not supported by device?')
            return -1


    def setfreq(self, freq):
        freq = (freq * 16) / 1000
        try:
            val = struct.pack( FREQUENCY_ST, long(0), long(0), freq)
            r = ioctl.ioctl(self.devfd, long(SETFREQ_NO), val)
        except:
            val = struct.pack( "L", freq)
            r = ioctl.ioctl(self.devfd, long(SETFREQ_NO_V4L), val)


    def getinput(self):
        r = ioctl.ioctl(self.devfd, GETINPUT_NO, struct.pack(INPUT_ST,0))
        return struct.unpack(INPUT_ST,r)[0]


    def setinput(self,value):
        r = ioctl.ioctl(self.devfd, SETINPUT_NO, struct.pack(INPUT_ST,value))


    def querycap(self):
        val = struct.pack( QUERYCAP_ST, "", "", "", 0, 0 )
        r = ioctl.ioctl(self.devfd, QUERYCAP_NO, val)
        return struct.unpack( QUERYCAP_ST, r )


    def enumstd(self, no):
        val = struct.pack( ENUMSTD_ST, no, 0, "", 0, 0, 0)
        r = ioctl.ioctl(self.devfd,ENUMSTD_NO,val)
        return struct.unpack( ENUMSTD_ST, r )


    def getstd(self):
        val = struct.pack( STANDARD_ST, 0 )
        r = ioctl.ioctl(self.devfd,GETSTD_NO, val)
        return struct.unpack( STANDARD_ST, r )[0]


    def setstd(self, value):
        val = struct.pack( STANDARD_ST, value )
        r = ioctl.ioctl(self.devfd,SETSTD_NO, val)


    def enuminput(self,index):
        val = struct.pack( ENUMINPUT_ST, index, "", 0,0,0,0,0)
        r = ioctl.ioctl(self.devfd,ENUMINPUT_NO,val)
        return struct.unpack( ENUMINPUT_ST, r )


    def getfmt(self):
        val = struct.pack( FMT_ST, 1L,0,0,0,0,0,0,0)
        try:
            r = ioctl.ioctl(self.devfd,GET_FMT_NO,val)
            return struct.unpack( FMT_ST, r )
        except IOError:
            log.warn('Failed to get format, not supported by device?')
            return (-1, -1, -1, -1, -1, -1, -1, -1)


    def setfmt(self, width, height):
        val = struct.pack( FMT_ST, 1L, width, height, 0L, 4L, 0L, 131072L, 0L)
        r = ioctl.ioctl(self.devfd,SET_FMT_NO,val)


    def getvbifmt(self):
        val = struct.pack( FMT_VBI_ST, 3L,0,0,0,0,0,0,0,0,0,0,0)
        r = ioctl.ioctl(self.devfd,GET_FMT_NO,val)
        return unpack_dict(FMT_VBI_ST, FMT_VBI_VARS, r)


    def setvbifmt(self, d):
        val = pack_dict( FMT_VBI_ST, FMT_VBI_VARS, d)
        r = ioctl.ioctl(self.devfd,GET_FMT_NO,val)
        return unpack_dict(FMT_VBI_ST, FMT_VBI_VARS, r)


    def gettuner(self, index):
        val = struct.pack( TUNER_ST, index, "", 0,0,0,0,0,0,0,0)
        r = ioctl.ioctl(self.devfd,GET_TUNER_NO,val)
        return unpack_dict( TUNER_ST, TUNER_VARS, r)


    def settuner(self,index,audmode):
        val = struct.pack( TUNER_ST, index, "", 0,0,0,0,0,audmode,0,0)
        r = ioctl.ioctl(self.devfd,SET_TUNER_NO,val)


    def getaudio(self,index):
        val = struct.pack( AUDIO_ST, index, "", 0,0)
        r = ioctl.ioctl(self.devfd,GET_AUDIO_NO,val)
        return struct.unpack( AUDIO_ST, r )


    def setaudio(self,index,mode):
        val = struct.pack( AUDIO_ST, index, "", mode, 0)
        r = ioctl.ioctl(self.devfd,SET_AUDIO_NO,val)
