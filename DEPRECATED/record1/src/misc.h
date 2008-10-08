/* File: misc.h
 *
 * Author: Sönke Schwardt <schwardt@tzi.de>
 *
 * $Id$
 *
 * Copyright (C) 2004 Sönke Schwardt <schwardt@users.sourceforge.net>
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
 */

#ifndef __MISC_H_
#define __MISC_H_

#include <iostream>
#include <string>
#include <sstream>
#include <utility>

#include <sys/time.h>
#include <time.h>


#define FN_CONFIG_FILE     "config"

template<typename T>
std::string to_string(const T& obj) {
  std::ostringstream t;
  t << obj;
  std::string res(t.str());
  return res;  
}

const int LOG_ERROR              = 1;
const int LOG_WARN               = 2;
const int LOG_INFO               = 4;
const int LOG_VERBOSE            = 8;
const int LOG_DEBUG              = 16;
const int LOG_DEBUG_TUNER        = 32;
const int LOG_DEBUG_DVBDEVICE    = 64;
const int LOG_DEBUG_FILTER       = 128;
const int LOG_DEBUG_OUTPUTPLUGIN = 256;
const int LOG_DEBUG_SCHEDULER    = 512;
const int LOG_DEBUG_RPCSERVER    = 1024;
const int LOG_DEBUG_REMUX        = 2048;
const int LOG_DEBUG_RINGBUFFER   = 4096;

#define printD(verbose, fmt, args...)                              \
  do {                                                             \
    if(::debug_level >= verbose){                                  \
      struct timeval tv;                                           \
      gettimeofday( &tv, NULL );                                   \
      struct tm *curtime;                                          \
      time_t now = time(NULL);                                     \
      curtime = localtime( &now );                                 \
      static char buf[8192];                                          \
      snprintf(buf, 8192, "%02d:%02d:%02d.%03d %12s:%04d (%s): " fmt, \
               curtime->tm_hour, curtime->tm_min,                     \
               curtime->tm_sec, ((int)tv.tv_usec / 1000),             \
	       __FILE__, __LINE__, __FUNCTION__, ##args);             \
      std::cout << buf;                                            \
    }                                                              \
  } while(0)


extern int      debug_level;

#endif
