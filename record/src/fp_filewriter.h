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

#ifndef __FP_FILEWRITER_H_
#define __FP_FILEWRITER_H_

#include <Python.h>
#include <vector>
#include <string>
#include "fp_generic.h"

class FPFilewriter : public FilterPlugin {
  public:

  FPFilewriter( const std::string &uri, int chunksize );
  void add_data( const std::string &data );
  void process_data();
  std::string get_data();
  ~FPFilewriter();

  private:
  int file_fd;             // opened chunk file 
  int file_size;           // actual chunk size
  int file_maxsize;        // maximum chunk size
  int file_counter;        // serial file number
  int file_size_total;     // summarized size of all chunks
  std::string file_name;   // output filename (may contain %)

  std::string buffer;      // buffer for caching data
  
  // close current chunk and open a new one
  void open_new_chunk();

};

PyObject *PyFilter_Filewriter(PyObject *self, PyObject* args);

#endif
