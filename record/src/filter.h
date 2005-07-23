/* File: filter.h
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

#ifndef __FILTER_H_
#define __FILTER_H_

#include <string>
#include <vector>
#include <map>

class OutputPlugin;

class FilterData {
  public:
  std::vector< int > pids;
  OutputPlugin      *op;
};

class Filter {

  std::map<int, FilterData>  id2filter;
  std::map<int, std::vector< OutputPlugin* > > pid2op;

  std::string buffer;      // buffer of filter object
  int idcounter;           // counter used for creating a new id

  static const int BUFFERSIZE = 18800;

  // scans buffer for MPEG-TS frames
  // params: none
  // returns: nothing
  void scan_buffer();

  public:

  Filter();
  ~Filter();

  // adds a new filter
  // params: fdata contains requested pids and outputplugin
  // returns: id for this filter
  int add_filter( FilterData &fdata );

  // removes an existing filter
  // params: id that shall be removed
  // returns: true if successfully removed
  bool remove_filter( int id );
  
  // process given dvb data
  // params: data
  // returns: nothing
  void process_data( std::string &data );
};

#endif
