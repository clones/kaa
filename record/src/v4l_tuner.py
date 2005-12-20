# -*- coding: iso-8859-1 -*-
# -----------------------------------------------------------------------
# v4l_tuner.py - V4L2 python interface.
# -----------------------------------------------------------------------
#
# Notes: http://bytesex.org/v4l/spec/
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
#   src/tv/v4l2.py by Thomas Schueppel <stain@cs.tu-berlin.de>, 
#                     Rob Shortt <rob@tvcentric.com>
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

# python imports
import logging
import os
import string
import struct
import sys
from types import *

# kaa imports
from kaa.base.ioctl import ioctl, IOR, IOW, IOWR
from v4l_frequencies import get_frequency, CHANLIST

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
GETFREQ_NO   = IOWR('V', 56, FREQUENCY_ST)
SETFREQ_NO   = IOW('V', 57, FREQUENCY_ST)

SETFREQ_NO_V4L = IOW('v', 15, "L")

QUERYCAP_ST  = "16s32s32sLL16x"
QUERYCAP_NO  = IOR('V',  0, QUERYCAP_ST)

ENUMSTD_ST   = "LQ24s2LL16x"
ENUMSTD_NO   = IOWR('V', 25, ENUMSTD_ST)

STANDARD_ST  = "Q"
GETSTD_NO    = IOR('V', 23, STANDARD_ST)
SETSTD_NO    = IOW('V', 24, STANDARD_ST)

ENUMINPUT_ST = "L32sLLLQL16x"
ENUMINPUT_NO = IOWR('V', 26, ENUMINPUT_ST)

INPUT_ST  = "L";
GETINPUT_NO  = IOR('V', 38, INPUT_ST)
SETINPUT_NO  = IOWR('V', 39, INPUT_ST)

FMT_ST = "L7L4x168x"
GET_FMT_NO = IOWR ('V',  4, FMT_ST)
SET_FMT_NO = IOWR ('V',  5, FMT_ST)

FMT_VBI_ST = "12L00x"
FMT_VBI_VARS = ('type', 'sampling_rate', 'offset', 'samples_per_line', 'sample_format',
                'start0', 'start1', 'count0', 'count1', 'flags', 'reserved0', 'reserved1')
GET_FMT_VBI_NO = IOWR ('V',  4, FMT_VBI_ST)
SET_FMT_VBI_NO = IOWR ('V',  5, FMT_VBI_ST)

# struct v4l2_tuner
TUNER_ST = "L32si5L2l16x"
TUNER_VARS = ('index', 'name', 'type', 'capabilities', 'rangelow', 'rangehigh',
              'rxsubchans', 'audmode', 'signal', 'afc')
GET_TUNER_NO = IOWR ('V', 29, TUNER_ST)
SET_TUNER_NO = IOW  ('V', 30, TUNER_ST)

AUDIO_ST = "L32sLL8x"
GET_AUDIO_NO = IOWR ('V', 33, AUDIO_ST)
SET_AUDIO_NO = IOW  ('V', 34, AUDIO_ST)

VIDIOC_STREAMON_ST = 'i'
VIDIOC_STREAMOFF_ST = 'i'
VIDIOC_STREAMON  = IOW('V', 18, VIDIOC_STREAMON_ST)
VIDIOC_STREAMOFF = IOW('V', 19, VIDIOC_STREAMOFF_ST)


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
    

class V4L(object):
    class _V4LChannel:
        def __init__(self, tunerid, name, frequency):
            self.tunerid   = tunerid
            self.name      = name
            self.frequency = frequency

        def __str__(self):
            s = '%s:%s:%s' % (self.tunerid, self.name, self.frequency)
            return s


    def __init__(self, device, norm, chanlist=None, channels=None, card_input=1):
        """
        """
        self.device = device
        self.card_input = card_input

        if not chanlist:
            # TODO: this will be removed, we have channels.conf now
            log.error('no chanlist supplied')
            self.chanlist = 'unknown'
            
        else:
            if not chanlist in CHANLIST.keys():
                log.error('bad chanlist "%s", setting to unknown' % chanlist)
                self.chanlist = 'unknown'
            else:
                self.chanlist = chanlist

        # Keep a dict of the channels we care about.
        self.channels = {}

        if channels:
            if type(channels) == ListType:
                self.parse_channels(channels)
            elif os.path.exists(channels):
                self.load_channels(channels)

        if not type(norm) is StringType or norm.upper() not in NORMS.keys():
            log.error('bad norm "%s", using NTSC as default' % norm)
            self.norm = 'NTSC'
        else:
            self.norm = norm.upper()

        self.devfd = -1
        self.open()

        #self.devfd = os.open(self.device, os.O_RDONLY)
        #if self.devfd < 0:
        #    log.error('failed to open %s, fd: %d' % (self.device, self.devfd))

        cardcaps          = self.querycap()
        self.driver       = cardcaps[0][:cardcaps[0].find('\0')]
        self.card         = cardcaps[1][:cardcaps[1].find('\0')]
        self.bus_info     = cardcaps[2]
        self.version      = cardcaps[3]
        self.capabilities = cardcaps[4]
    
        self.setstd(NORMS.get(self.norm))
        self.setinput(self.card_input)

        # XXX TODO: make a good way of setting the capture resolution
        # self.setfmt(int(width), int(height))
    

    def load_channels(self, channels_conf):
        channels = []

        try:
            cfile = open(channels_conf, 'r')
        except Exception, e:
            log.error('failed to read channels.conf (%s): %s' % (channels, e))
            return

        for line in cfile.readlines():
            good = line.split('#', 1)[0].rstrip('\n')
            if len(good.strip()) == 0: continue
            channels.append(good)

        cfile.close()

        self.parse_channels(channels)


    def parse_channels(self, channels):
        if type(channels) is not ListType:
            log.error('Error parsing channels: not a list')
            return False

        for channel in channels:
            c = channel.split(':', 2)

            # first field: tunerid
            tunerid = c[0]

            if len(c) > 1:
                # second field: name
                name = c[1]
            else:
                name = 'undefined'

            if len(c) > 2:
                # third field: frequency
                frequency = c[2]
            else:
                # no frequency specified, look it up
                frequency = get_frequency(tunerid, self.chanlist)

            if frequency == 0:
                log.error('no frequency for %s, either specify in config or check your chanlist' % tunerid)
                continue

            chan = self._V4LChannel(tunerid, name, frequency) 
            log.info('adding channel: %s' % chan)
            self.channels[chan.tunerid] = chan


    def get_bouquet_list(self):
        """
        Return bouquets as a list
        """
        bl = []
        for c in self.channels.values():
            bl.append([])
            bl[-1].append(c.tunerid)

        return bl


    def open(self):
        self.devfd = os.open(self.device, os.O_RDONLY | os.O_NONBLOCK)
        if self.devfd < 0:
            log.error('failed to open %s, fd: %d' % (self.device, self.devfd))
            return -1

        return self.devfd


    def close(self):
        os.close(self.devfd)


    def getfreq(self):
        val = struct.pack( FREQUENCY_ST, 0,0,0 )
        try:
            r = ioctl(self.devfd, GETFREQ_NO, val)
            (junk,junk, freq, ) = struct.unpack(FREQUENCY_ST, r)
            return freq
        except IOError:
            log.warn('Failed to get frequency, not supported by device?') 
            return -1


    def setchannel(self, channel):
        freq = get_frequency(channel, self.chanlist)

        log.debug('setting channel to %s (%d)' % (channel, freq))

        freq *= 16

        # The folowing check for TUNER_LOW capabilities was not working for
        # me... needs further investigation. 
        # if not (self.capabilities & V4L2_TUNER_CAP_LOW):
        #     # Tune in MHz.
        #     freq /= 1000
        freq /= 1000

        try:
            self.setfreq(freq)
        except:
            self.setfreq_old(freq)
      

    def setfreq_old(self, freq):
        val = struct.pack( "L", freq)
        r = ioctl(self.devfd, long(SETFREQ_NO_V4L), val)        


    def setfreq(self, freq):
        val = struct.pack( FREQUENCY_ST, long(0), long(0), freq)
        r = ioctl(self.devfd, long(SETFREQ_NO), val)


    def getinput(self):
        r = ioctl(self.devfd, GETINPUT_NO, struct.pack(INPUT_ST,0))
        return struct.unpack(INPUT_ST,r)[0]
  

    def setinput(self,value):
        r = ioctl(self.devfd, SETINPUT_NO, struct.pack(INPUT_ST,value))


    def querycap(self):
        val = struct.pack( QUERYCAP_ST, "", "", "", 0, 0 )
        r = ioctl(self.devfd, QUERYCAP_NO, val)
        return struct.unpack( QUERYCAP_ST, r )


    def enumstd(self, no):
        val = struct.pack( ENUMSTD_ST, no, 0, "", 0, 0, 0)
        r = ioctl(self.devfd,ENUMSTD_NO,val)
        return struct.unpack( ENUMSTD_ST, r )


    def getstd(self):
        val = struct.pack( STANDARD_ST, 0 )
        r = ioctl(self.devfd,GETSTD_NO, val)
        return struct.unpack( STANDARD_ST, r )[0]


    def setstd(self, value):
        val = struct.pack( STANDARD_ST, value )
        r = ioctl(self.devfd,SETSTD_NO, val)


    def enuminput(self,index):
        val = struct.pack( ENUMINPUT_ST, index, "", 0,0,0,0,0)
        r = ioctl(self.devfd,ENUMINPUT_NO,val)
        return struct.unpack( ENUMINPUT_ST, r )


    def getfmt(self):  
        val = struct.pack( FMT_ST, 1L,0,0,0,0,0,0,0)
        try:
            r = ioctl(self.devfd,GET_FMT_NO,val)
            return struct.unpack( FMT_ST, r )
        except IOError:
            log.warn('Failed to get format, not supported by device?') 
            return (-1, -1, -1, -1, -1, -1, -1, -1)


    def setfmt(self, width, height):
        val = struct.pack( FMT_ST, 1L, width, height, 0L, 4L, 0L, 131072L, 0L)
        r = ioctl(self.devfd,SET_FMT_NO,val)


    def getvbifmt(self):  
        val = struct.pack( FMT_VBI_ST, 3L,0,0,0,0,0,0,0,0,0,0,0)
        r = ioctl(self.devfd,GET_FMT_NO,val)
        return unpack_dict(FMT_VBI_ST, FMT_VBI_VARS, r)


    def setvbifmt(self, d):  
        val = pack_dict( FMT_VBI_ST, FMT_VBI_VARS, d)
        r = ioctl(self.devfd,GET_FMT_NO,val)
        return unpack_dict(FMT_VBI_ST, FMT_VBI_VARS, r)


    def gettuner(self, index):
        val = struct.pack( TUNER_ST, index, "", 0,0,0,0,0,0,0,0)
        return unpack_dict( TUNER_ST, TUNER_VARS, ioctl(self.devfd,GET_TUNER_NO,val))


    def settuner(self,index,audmode):
        val = struct.pack( TUNER_ST, index, "", 0,0,0,0,0,audmode,0,0)
        r = ioctl(self.devfd,SET_TUNER_NO,val)


    def getaudio(self,index):
        val = struct.pack( AUDIO_ST, index, "", 0,0)
        r = ioctl(self.devfd,GET_AUDIO_NO,val)
        return struct.unpack( AUDIO_ST, r )


    def setaudio(self,index,mode):
        val = struct.pack( AUDIO_ST, index, "", mode, 0)
        r = ioctl(self.devfd,SET_AUDIO_NO,val)


    def settings_as_string(self):
        s =  'Driver: %s\n' % self.driver
        s += 'Card: %s\n' % self.card
        s += 'Version: %s\n' % self.version
        s += 'Capabilities: %s\n' % self.capabilities

        s += 'Enumerating supported Standards.\n'
        try:
            for i in range(0,255):
                (index,id,name,junk,junk,junk) = self.enumstd(i)
                s += '  %i: 0x%x %s\n' % (index, id, name)
        except:
            pass
        s += 'Current Standard is: 0x%x\n' % self.getstd()

        s += 'Enumerating supported Inputs.\n'
        try:
            for i in range(0,255):
                (index,name,type,audioset,tuner,std,status) = self.enuminput(i)
                s += '  %i: %s\n' % (index, name)
        except:
            pass
        s += 'Input: %i\n' % self.getinput()

        (buf_type, width, height, pixelformat, field, bytesperline,
         sizeimage, colorspace) = self.getfmt()
        s += 'Width: %i, Height: %i\n' % (width,height)

        freq = self.getfreq()
        s += 'Read Frequency: %d (%d)' % (freq, freq*1000/16)
        return s


    def print_settings(self):
        log.info('Settings:\n%s' %self.settings_as_string())
