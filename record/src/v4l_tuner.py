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

TUNER_ST = "L32sLLLLLLll16x"
GET_TUNER_NO = IOWR ('V', 29, TUNER_ST)
SET_TUNER_NO = IOW  ('V', 30, TUNER_ST)

AUDIO_ST = "L32sLL8x"
GET_AUDIO_NO = IOWR ('V', 33, AUDIO_ST)
SET_AUDIO_NO = IOW  ('V', 34, AUDIO_ST)


V4L2_TUNER_CAP_LOW    = 0x0001
V4L2_TUNER_CAP_NORM   = 0x0002
V4L2_TUNER_CAP_STEREO = 0x0010
V4L2_TUNER_CAP_LANG2  = 0x0020
V4L2_TUNER_CAP_SAP    = 0x0020
V4L2_TUNER_CAP_LANG1  = 0x0040


NORMS = { 'NTSC'  : 0x3000,
          'PAL'   : 0xff,
          'SECAM' : 0x7f0000  }


class Videodev(object):
    def __init__(self, device, norm, chanlist=None, card_input=1, 
                 custom_frequencies=None):
        """
        """
        self.device = device
        self.card_input = card_input

        if not chanlist:
            if not custom_frequencies:
                log.error('no chanlist or custom_frequencies supplied')
                log.error('you must specify at least one to tune channels')
                self.chanlist = 'unknown'
            
        else:
            if not chanlist in CHANLIST.keys():
                log.error('bad chanlist "%s", setting to unknown' % chanlist)
                self.chanlist = 'unknown'
            else:
                self.chanlist = chanlist

        if not type(norm) is StringType or norm.upper() not in NORMS.keys():
            log.error('bad norm "%s", using NTSC as default' % norm)
            self.norm = 'NTSC'
        else:
            self.norm = norm.upper()

        if not type(custom_frequencies) == DictType:
            self.custom_frequencies = {}
        else:
            self.custom_frequencies = custom_frequencies

        self.devfd = os.open(self.device, os.O_TRUNC)
        if self.devfd < 0:
            log.error('failed to open %s, fd: %d' % (self.device, self.devfd))

        cardcaps          = self.querycap()
        self.driver       = cardcaps[0]
        self.card         = cardcaps[1]
        self.bus_info     = cardcaps[2]
        self.version      = cardcaps[3]
        self.capabilities = cardcaps[4]
    
        self.setstd(NORMS.get(self.norm))
        self.setinput(self.card_input)

        # XXX TODO: make a good way of setting the capture resolution
        # self.setfmt(int(width), int(height))
    

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
        freq = self.custom_frequencies.get(channel)

        if freq:
            log.debug('using custom frequency %d for channel %s' % (freq, channel)) 
        else:
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
        val = struct.pack( FMT_ST, 0,0,0,0,0,0,0,0)
        try:
            r = ioctl(self.devfd,GET_FMT_NO,val)
            return struct.unpack( FMT_ST, r )
        except IOError:
            log.warn('Failed to get format, not supported by device?') 
            return (-1, -1, -1, -1, -1, -1, -1, -1)


    def setfmt(self, width, height):
        val = struct.pack( FMT_ST, 1L, width, height, 0L, 4L, 0L, 131072L, 0L)
        r = ioctl(self.devfd,SET_FMT_NO,val)


    def gettuner(self,index):
        val = struct.pack( TUNER_ST, index, "", 0,0,0,0,0,0,0,0)
        r = ioctl(self.devfd,GET_TUNER_NO,val)
        return struct.unpack( TUNER_ST, r )


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


    def print_settings(self):
        log.info('Driver: %s' % self.driver)
        log.info('Card: %s' % self.card)
        log.info('Version: %s' % self.version)
        log.info('Capabilities: %s' % self.capabilities)

        log.info('Enumerating supported Standards.')
        try:
            for i in range(0,255):
                (index,id,name,junk,junk,junk) = self.enumstd(i)
                log.info('  %i: 0x%x %s' % (index, id, name))
        except:
            pass
        log.info('Current Standard is: 0x%x' % self.getstd())

        log.info('Enumerating supported Inputs.')
        try:
            for i in range(0,255):
                (index,name,type,audioset,tuner,std,status) = self.enuminput(i)
                log.info('  %i: %s' % (index, name))
        except:
            pass
        log.info('Input: %i' % self.getinput())

        (buf_type, width, height, pixelformat, field, bytesperline,
         sizeimage, colorspace) = self.getfmt()
        log.info('Width: %i, Height: %i' % (width,height))

        freq = self.getfreq()
        log.info('Read Frequency: %d (%d)' % (freq, freq*1000/16))


