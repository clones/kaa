/*
 * File: ringbuffer.h
 *
 * $Id$
 *
 * Copyright (C) 2005 S�nke Schwardt <schwardt@users.sourceforge.net>
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

#ifndef __RINGBUFFER_H
#define __RINGBUFFER_H

/* #include "tools.h" */
#include <inttypes.h>
#include <time.h>

typedef unsigned char uchar;

class cRingBuffer {
private:
  int putTimeout;
  int getTimeout;
  int size;
  time_t lastOverflowReport;
  int overflowCount;
  int overflowBytes;
protected:
  int maxFill;//XXX
  int lastPercent;
  bool statistics;//XXX
  void UpdatePercentage(int Fill);
  void WaitForPut(void);
  void WaitForGet(void);
  void EnablePut(void);
  void EnableGet(void);
  virtual void Clear(void) = 0;
  virtual int Available(void) = 0;
  virtual int Free(void) { return Size() - Available() - 1; }
  int Size(void) { return size; }
public:
  cRingBuffer(int Size, bool Statistics = false);
  virtual ~cRingBuffer();
  void SetTimeouts(int PutTimeout, int GetTimeout);
  void ReportOverflow(int Bytes);
  };

class cRingBufferLinear : public cRingBuffer {
//#define DEBUGRINGBUFFERS
#ifdef DEBUGRINGBUFFERS
private:
  int lastHead, lastTail;
  int lastPut, lastGet;
  static cRingBufferLinear *RBLS[];
  static void AddDebugRBL(cRingBufferLinear *RBL);
  static void DelDebugRBL(cRingBufferLinear *RBL);
public:
  static void PrintDebugRBL(void);
#endif
private:
  int margin, head, tail;
  int gotten;
  uchar *buffer;
  char *description;
public:
  cRingBufferLinear(int Size, int Margin = 0, bool Statistics = false, const char *Description = NULL);
    ///< Creates a linear ring buffer.
    ///< The buffer will be able to hold at most Size-Margin-1 bytes of data, and will
    ///< be guaranteed to return at least Margin bytes in one consecutive block.
    ///< The optional Description is used for debugging only.
  virtual ~cRingBufferLinear();
  virtual int Available(void);
  virtual int Free(void) { return Size() - Available() - 1 - margin; }
  virtual void Clear(void);
    ///< Immediately clears the ring buffer.
/*   int Read(int FileHandle, int Max = 0); */
    ///< Reads at most Max bytes from FileHandle and stores them in the
    ///< ring buffer. If Max is 0, reads as many bytes as possible.
    ///< Only one actual read() call is done.
    ///< \return Returns the number of bytes actually read and stored, or
    ///< an error value from the actual read() call.
  int Put(const uchar *Data, int Count);
    ///< Puts at most Count bytes of Data into the ring buffer.
    ///< \return Returns the number of bytes actually stored.
  uchar *Get(int &Count);
    ///< Gets data from the ring buffer.
    ///< The data will remain in the buffer until a call to Del() deletes it.
    ///< \return Returns a pointer to the data, and stores the number of bytes
    ///< actually available in Count. If the returned pointer is NULL, Count has no meaning.
  void Del(int Count);
    ///< Deletes at most Count bytes from the ring buffer.
    ///< Count must be less or equal to the number that was returned by a previous
    ///< call to Get().
  };

enum eFrameType { ftUnknown, ftVideo, ftAudio, ftDolby };

class cFrame {
  friend class cRingBufferFrame;
private:
  cFrame *next;
  uchar *data;
  int count;
  eFrameType type;
  int index;
public:
  cFrame(const uchar *Data, int Count, eFrameType = ftUnknown, int Index = -1);
    ///< Creates a new cFrame object.
    ///< If Count is negative, the cFrame object will take ownership of the given
    ///< Data. Otherwise it will allocate Count bytes of memory and copy Data.
  ~cFrame();
  uchar *Data(void) const { return data; }
  int Count(void) const { return count; }
  eFrameType Type(void) const { return type; }
  int Index(void) const { return index; }
  };

class cRingBufferFrame : public cRingBuffer {
private:
  cFrame *head;
  int currentFill;
  void Delete(cFrame *Frame);
  void Lock(void) {}
  void Unlock(void) {}
public:
  cRingBufferFrame(int Size, bool Statistics = false);
  virtual ~cRingBufferFrame();
  virtual int Available(void);
  virtual void Clear(void);
    // Immediately clears the ring buffer.
  bool Put(cFrame *Frame);
    // Puts the Frame into the ring buffer.
    // Returns true if this was possible.
  cFrame *Get(void);
    // Gets the next frame from the ring buffer.
    // The actual data still remains in the buffer until Drop() is called.
  void Drop(cFrame *Frame);
    // Drops the Frame that has just been fetched with Get().
  };

#endif // __RINGBUFFER_H
