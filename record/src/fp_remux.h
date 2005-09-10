/* File: op_filewriter.h
 *
 * Author: Sönke Schwardt <schwardt@users.sourceforge.net>
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

#ifndef __FP_REMUX_H_
#define __FP_REMUX_H_

#include <vector>
#include <string>
#include "fp_generic.h"
#include "remux.h"

class FPRemux : public FilterPlugin {
  public:

  FPRemux();
  ~FPRemux();

  void add_data( const std::string &data );
  void process_data();
  std::string get_data();

  void set_pids( int Pid_V,                  // video pid
		 std::vector<int> Pids_A,    // audio pids
		 std::vector<int> Pids_D,    // dolby audio pids
		 std::vector<int> Pids_S );  // subtitle pids

  private:
  cRemux *remux;

  std::string buffer_in;   // buffer for caching data  
  std::string buffer_out;  // buffer for caching data  

  const static int DEFAULT_MAX_BUFFERSIZE = 188 * 1000;
};

#endif
