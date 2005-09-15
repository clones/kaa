/* File: fdsplitter.h
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

#ifndef __FDSPLITTER_H_
#define __FDSPLITTER_H_

#include <string>
#include <vector>
#include <map>

#include "filter.h"

class FDSplitter {

  std::map<int, FilterChain>  id2filter;
  std::map<int, std::vector< int > > pid2id;

  std::string buffer;      // buffer of filter object
  int idcounter;           // counter used for creating a new id
  int inputtype;
  int fd;

  static const int BUFFERSIZE = 18800;

  // process given dvb data
  // params: data
  // returns: nothing
  void process_data();

  // scans buffer for MPEG-TS frames and adds frames to filter chains
  // params: none
  // returns: nothing
  void process_new_data_TS();

  // adds data to filter chains
  // params: none
  // returns: nothing
  void process_new_data_RAW();
  
  // iterates through all filter chains and processes data
  // params: none
  // returns: nothing
  void process_filter_chain();

  public:

  enum InputType { INPUT_RAW, INPUT_TS, INPUT_LAST };

  FDSplitter( int fd );
  ~FDSplitter();

  // set filter chain handling
  // params: type of input
  // returns: nothing
  void set_input_type( InputType inputtype );

  // adds a new filter
  // params: fdata contains requested pids and outputplugin
  // returns: id for this filter
  int add_filter_chain( FilterChain &fdata );

  // removes an existing filter
  // params: id that shall be removed
  // returns: true if successfully removed
  bool remove_filter_chain( int id );
  
  // copy given dvb data to internal buffer
  // params: data
  // returns: nothing
  void add_data( std::string &data );

  // callback for notifier
  void read_fd_data();
};

#endif
