#if 0
# -----------------------------------------------------------------------
# $Id$
# -----------------------------------------------------------------------
# $Log$
# Revision 1.8  2003/07/10 13:05:05  the_krow
# o id3v2 tabled added to eyed3
# o type changed to MUSIC
#
# Revision 1.7  2003/07/02 20:15:42  dischi
# return nothing, not 0
#
# Revision 1.6  2003/06/30 13:17:18  the_krow
# o Refactored mediainfo into factory, synchronizedobject
# o Parsers now register directly at mmpython not at mmpython.mediainfo
# o use mmpython.Factory() instead of mmpython.mediainfo.get_singleton()
# o Bugfix in PNG parser
# o Renamed disc.AudioInfo into disc.AudioDiscInfo
# o Renamed disc.DataInfo into disc.DataDiscInfo
#
# Revision 1.5  2003/06/30 11:38:22  dischi
# bugfix
#
# Revision 1.4  2003/06/29 18:30:14  dischi
# many many fixes
#
# Revision 1.3  2003/06/29 12:03:41  dischi
# fixed it to be _real_ eyed3 info
#
# Revision 1.2  2003/06/20 19:17:22  dischi
# remove filename again and use file.name
#
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
import mmpython

from eyeD3 import tag as eyeD3_tag
from eyeD3 import frames as eyeD3_frames
import os
import traceback

MP3_INFO_TABLE = { "APIC": "picture",
                   "LINK": "link",
                   "TALB": "album",
                   "TCOM": "composer",
                   "TCOP": "copyright",
                   "TDOR": "release",
                   "TYER": "date",
                   "TEXT": "text",
                   "TIT2": "title",
                   "TLAN": "language",
                   "TLEN": "length",
                   "TMED": "media_type",
                   "TPE1": "artist",
                   "TPE2": "artist",
                   "TRCK": "trackno" }

class eyeD3Info(mediainfo.MusicInfo):
   
   fileName       = str();
   fileSize       = int();
   
   def __init__(self, file, tagVersion = eyeD3_tag.ID3_ANY_VERSION):
      mediainfo.MusicInfo.__init__(self)
      self.fileName = file.name;
      self.valid = 1
      self.mime = 'audio/mp3'

      if not eyeD3_tag.isMp3File(file.name):
         self.valid = 0
         return

      id3 = None
      try:
         id3 = eyeD3_tag.Mp3AudioFile(file.name)
      except eyeD3_tag.TagException:
         try:
            id3 = eyeD3_tag.Mp3AudioFile(file.name)
         except eyeD3_tag.InvalidAudioFormatException:
            # File is not an MP3
            self.valid = 0
            return
         except:
            # The MP3 tag decoder crashed, assume the file is still
            # MP3 and try to play it anyway
            print 'music: oops, mp3 tag parsing failed!'
            print 'music: filename = "%s"' % file.name
            traceback.print_exc()
      except:
         # The MP3 tag decoder crashed, assume the file is still
         # MP3 and try to play it anyway
         print 'music: oops, mp3 tag parsing failed!'
         print 'music: filename = "%s"' % file.name
         traceback.print_exc()

      if not self.valid:
         return

      if mediainfo.DEBUG > 1:
         print id3.tag.frames
      try:
         if id3 and id3.tag:
            for k in MP3_INFO_TABLE:
               if id3.tag.frames[k]:
                  if k == 'APIC':
                     pass
                     #setattr(self, MP3_INFO_TABLE[k], id3.tag.frames[k][0].imageData)
                  else:
                     setattr(self, MP3_INFO_TABLE[k], id3.tag.frames[k][0].text)
            if id3.tag.getYear():
               self.date = id3.tag.getYear()
            tab = {}
            for f in id3.tag.frames:
                if f.__class__ is eyeD3_frames.TextFrame:                
                    tab[f.header.id] = f.text
                elif f.__class__ is eyeD3_frames.UserTextFrame:
                    tab[f.header.id] = f.text
                elif f.__class__ is eyeD3_frames.DateFrame:
                    tab[f.header.id] = f.date_str
                elif f.__class__ is eyeD3_frames.CommentFrame:
                    tab[f.header.id] = f.comment
                elif f.__class__ is eyeD3_frames.URLFrame:
                    tab[f.header.id] = f.url
                elif f.__class__ is eyeD3_frames.UserURLFrame:
                    tab[f.header.id] = f.url
                else:
                    print f.__class__
            self.appendtable('id3v2', tab, 'en')
         if id3:
            self.length = id3.getPlayTime()
      except:
         traceback.print_exc()

      
         
mmpython.registertype( 'audio/mp3', ('mp3',), mediainfo.TYPE_MUSIC, eyeD3Info )
