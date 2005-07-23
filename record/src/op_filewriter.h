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

#ifndef __OP_FILEWRITER_H_
#define __OP_FILEWRITER_H_

#include <vector>
#include <string>
#include "op_generic.h"
#include "remux.h"

class OutputPluginFilewriter : public OutputPlugin {
  public:
  enum FileType { FT_RAW, FT_MPEG };

  OutputPluginFilewriter( const std::string &uri, int chunksize, FileType ftype  );
  virtual void set_pids( int Pid_V, std::vector<int> Pids_A, 
			 std::vector<int> Pids_D, std::vector<int> Pids_S );
  void process_data( const std::string &data );
  void flush();  
  ~OutputPluginFilewriter();


  private:
  int file_fd;             // opened chunk file 
  int file_size;           // actual chunk size
  int file_maxsize;        // maximum chunk size
  int file_counter;        // serial file number
  int file_size_total;     // summarized size of all chunks
  std::string file_name;   // output filename (may contain %)
  FileType file_type;      // type of output file 

  cRemux *remux;

  std::string buffer_in;   // buffer for caching data
  std::string buffer_out;  // buffer for caching data
  
  const static int DEFAULT_MAX_FILESIZE = 10 * 1024 * 1024; // 10 MiB
  const static int DEFAULT_MAX_BUFFERSIZE = 188 * 1000;

  // close current chunk and open a new one
  void open_new_chunk();

};

#endif
