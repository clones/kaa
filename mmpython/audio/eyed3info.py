#if 0
# -----------------------------------------------------------------------
# $Id$
# -----------------------------------------------------------------------
# $Log$
# Revision 1.1  2003/06/09 23:13:21  the_krow
# bugfix: unknown files are now resetted before trying if they are valid
# first rudimentary eyed3 mp3 parser added
#
#
# -----------------------------------------------------------------------
# MMPython - Media Metadata for Python
# Copyright (C) 2003 Thomas Schueppel, et. al
#
# This program is free software; you can redistribute it and/or
# modify it under the terms of the GNU General Public License as
# published by the Free Software Foundation; either version 2 of the
# License, or (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 59 Temple Place, Suite 330, Boston, MA 02111-1307
# USA
#
# Most of the code of this module was taken from Vivake Guptas mp3info
# code. Below is his copyright notice. All credit to him.
#
# Copyright (c) 2002 Vivake Gupta (vivakeATomniscia.org).  All rights reserved.
# This software is maintained by Vivake (vivakeATomniscia.org) and is available at:
#     http://www.omniscia.org/~vivake/python/MP3Info.py
#
#


from mmpython import mediainfo

import eyeD3.mp3 as mp3
import eyeD3.utils as utils
import eyeD3.tag as eyeD3_tag
from eyeD3.frames import *
from eyeD3.binfuncs import *
from eyeD3.tag import *
 
import os
    
################################################################################
# ID3 tag class.  The class is capable of reading v1 and v2 tags.  ID3 v1.x
# are converted to v2 frames.
################################################################################
class eyeD3Info(mediainfo.MusicInfo):
   
   fileName       = str();
   fileSize       = int();
   header         = mp3.Header();
   xingHeader     = None;
   tag            = Tag();
   invalidFileExc = InvalidAudioFormatException("File is not mp3");
   # Number of seconds required to play the audio file.

   def __init__(self, file, fileName, tagVersion = eyeD3_tag.ID3_ANY_VERSION):
      mediainfo.MusicInfo.__init__(self)
      self.fileName = fileName;
      self.valid = 1
      self.mime = 'audio/mp3'

      if not eyeD3_tag.isMp3File(fileName):
         raise self.invalidFileExc;

      # Parse ID3 tag.
      tag = Tag();
      hasTag = tag.link(file, tagVersion);
      # Find the first mp3 frame.
      if tag.isV1():
         framePos = 0;
      elif not hasTag:
         framePos = 0;
         tag = None;
      else:
         # XXX: Note that v2.4 allows for appended tags; account for that.
         framePos = tag.header.SIZE + tag.header.tagSize;
      file.seek(framePos);
      bString = file.read(4);
      if len(bString) < 4:
         raise InvalidAudioFormatException("Unable to find a valid mp3 "\
                                           "frame");
      frameHead = bin2dec(bytes2bin(bString));
      header = mp3.Header();
      # Keep reading until we find a valid mp3 frame header.
      while not header.isValid(frameHead):
         frameHead <<= 8;
         bString = file.read(1);
         if len(bString) != 1:
            raise InvalidAudioFormatException("Unable to find a valid mp3 "\
                                              "frame");
         frameHead |= ord(bString[0]);
      TRACE_MSG("mp3 header %x found at position: %d (0x%x)" % \
                (frameHead, file.tell() - 4, file.tell() - 4));

      # Decode the header.
      try:
         header.decode(frameHead);
         # Check for Xing header inforamtion which will always be in the
         # first "null" frame.
         file.seek(-4, 1);
         mp3Frame = file.read(header.frameLength);
         if mp3Frame.find("Xing") != -1:
            xingHeader = mp3.XingHeader();
            if not xingHeader.decode(mp3Frame):
               raise InvalidAudioFormatException("Corrupt Xing header");
         else:
            xingHeader = None;
      except mp3.Mp3Exception, ex:
         raise InvalidAudioFormatException(str(ex));

      # Compute track play time.
      tpf = mp3.computeTimePerFrame(header);
      if xingHeader:
         self.length = int(tpf * xingHeader.numFrames);
      else:
         length = self.getSize();
         if tag and tag.isV2():
            length -= tag.header.SIZE + tag.header.tagSize;
            # Handle the case where there is a v2 tag and a v1 tag.
            file.seek(-128, 2)
            if file.read(3) == "TAG":
               length -= 128;
         elif tag and tag.isV1():
            length -= 128;
         self.length = int((length / header.frameLength) * tpf);    

      self.header = header;
      self.xingHeader = xingHeader;
      self.tag = tag;
      self.bitrate = self.getBitRate()[1]
      self.appendtable('ID3',self.tag.frames)

   def getTag(self):
      return self.tag;

   def getSize(self):
      if not self.fileSize:
         self.fileSize = os.stat(self.fileName)[ST_SIZE];
      return self.fileSize;

   def getPlayTimeString(self):
      total = self.length;
      h = total / 3600;
      m = (total % 3600) / 60;
      s = (total % 3600) % 60;
      if h:
         timeStr = "%d:%.2d:%.2d" % (h, m, s);
      else:
         timeStr = "%d:%.2d" % (m, s);
      return timeStr;

   # Returns a tuple.  The first value is a boolean which if true means the
   # bit rate returned in the second value is variable.
   def getBitRate(self):
      xHead = self.xingHeader;
      if xHead:
         tpf = mp3.computeTimePerFrame(self.header);
         br = int((xHead.numBytes * 8) / (tpf * xHead.numFrames * 1000));
         vbr = 1;
      else:
         br = self.header.bitRate;
         vbr = 0;
      return (vbr, br);

   def getBitRateString(self):
      (vbr, bitRate) = self.getBitRate();
      brs = "%d kb/s" % bitRate;
      if vbr:
         brs = "~" + brs;
      return brs;
         
factory = mediainfo.get_singleton()
factory.register( 'audio/mp3', ('mp3',), mediainfo.TYPE_AUDIO, eyeD3Info )
