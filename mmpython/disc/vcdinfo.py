#if 0 /*
# -----------------------------------------------------------------------
# vcdinfo.py - parse vcd track informations
# -----------------------------------------------------------------------
# $Id$
#
# -----------------------------------------------------------------------
# Copyright (C) 2003 Thomas Schueppel, Dirk Meyer
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
#endif


from mmpython import mediainfo
import cdrom

class VCDInfo(mediainfo.DiscInfo):
    def __init__(self,device):
        mediainfo.DiscInfo.__init__(self)
        self.context = 'video'
        self.offset = 0
        self.valid = self.isDisc(device)
        self.mime = 'video/vcd'
        self.type = 'vcd video'        

    def isDisc(self, device):
        if mediainfo.DiscInfo.isDisc(self, device) != 2:
            return 0
        
        # brute force reading of the device to find out if it is a VCD
        f = open(device,'rb')
        f.seek(32808, 0)
        buffer = f.read(50000)
        f.close()

        if buffer.find('SVCD') > 0 and buffer.find('TRACKS.SVD') > 0 and \
               buffer.find('ENTRIES.SVD') > 0:
            print 'This is a SVCD'

        elif buffer.find('INFO.VCD') > 0 and buffer.find('ENTRIES.VCD') > 0:
            print 'This is a VCD'

        else:
            return None

        # read the tracks to generate the title list
        device = open(device)
        (first, last) = cdrom.toc_header(device)

        lmin = 0
        lsec = 0

        num = 0
        for i in range(first, last + 2):
            if i == last + 1:
                min, sec, frames = cdrom.leadout(device)
            else:
                min, sec, frames = cdrom.toc_entry(device, i)
            if num:
                self.tracks.append(min-lmin)
            num += 1
            lmin, lsec = min, sec
        device.close()
        return 1

    
factory = mediainfo.get_singleton()  
factory.register( 'video/vcd', mediainfo.DEVICE, mediainfo.TYPE_AV, VCDInfo )
