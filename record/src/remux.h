/*
 * File: remux.h
 *
 * $Id$
 *
 * Copyright (C) 2005 Sönke Schwardt <schwardt@users.sourceforge.net>
 *
 * This program is free software; you can redistribute it and/or modify
 * it under the terms of the GNU General Public License as published by
 * the Free Software Foundation; either version 2, or (at your option)
 * any later version.
 *
 * This program is distributed in the hope that it will be useful,
 * but WITHOUT ANY WARRANTY; without even the implied warranty of
 * MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
 * GNU General Public License for more details.
 *
 * You should have received a copy of the GNU General Public License
 * along with this program; if not, write to the Free Software
 * Foundation, Inc., 59 Temple Place - Suite 330, Boston, MA 02111-1307, USA.
 *
 * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * *
 *
 * The parts of this code that implement TS2PES and Remux have been
 * taken from VDR project. (http://www.cadsoft.de/people/kls/vdr/)
 *
 */

#ifndef __REMUX_H
#define __REMUX_H

#include <time.h> //XXX FIXME: DVB/linux/dvb/dmx.h should include <time.h> itself!!!
// #include <linux/dvb/dmx.h>
#include "ringbuffer.h"
// #include "tools.h"

// Picture types:
#define NO_PICTURE 0
#define I_FRAME    1
#define P_FRAME    2
#define B_FRAME    3

#define MAXTRACKS 64
#define MAXAPIDS 32
#define MAXDPIDS 16
#define MAXSPIDS 8

#define MALLOC(type, size)  (type *)malloc(sizeof(type) * (size))

class cTS2PES;

class cRemux {
private:
  bool exitOnFailure;
  bool isRadio;
  int numUPTerrors;
  bool synced;
  int skipped;
  cTS2PES *ts2pes[MAXTRACKS];
  int numTracks;
  cRingBufferLinear *resultBuffer;
  int resultSkipped;
  int GetPid(const uchar *Data);
  int GetPacketLength(const uchar *Data, int Count, int Offset);
  int ScanVideoPacket(const uchar *Data, int Count, int Offset, uchar &PictureType);
public:
  cRemux(int VPid, const int *APids, const int *DPids, const int *SPids, bool ExitOnFailure = false);
       ///< Creates a new remuxer for the given PIDs. VPid is the video PID, while
       ///< APids, DPids and SPids are pointers to zero terminated lists of audio,
       ///< dolby and subtitle PIDs (the pointers may be NULL if there is no such
       ///< PID). If ExitOnFailure is true, the remuxer will initiate an "emergency
       ///< exit" in case of problems with the data stream.
  ~cRemux();
  int Put(const uchar *Data, int Count);
       ///< Puts at most Count bytes of Data into the remuxer.
       ///< \return Returns the number of bytes actually consumed from Data.
  uchar *Get(int &Count, uchar *PictureType = NULL);
       ///< Gets all currently available data from the remuxer.
       ///< \return Count contains the number of bytes the result points to, and
       ///< PictureType (if not NULL) will contain one of NO_PICTURE, I_FRAME, P_FRAME
       ///< or B_FRAME.
  void Del(int Count);
       ///< Deletes Count bytes from the remuxer. Count must be the number returned
       ///< from a previous call to Get(). Several calls to Del() with fractions of
       ///< a previously returned Count may be made, but the total sum of all Count
       ///< values must be exactly what the previous Get() has returned.
  void Clear(void);
       ///< Clears the remuxer of all data it might still contain, keeping the PID
       ///< settings as they are.
  static void SetBrokenLink(uchar *Data, int Length);
  };

#endif // __REMUX_H
