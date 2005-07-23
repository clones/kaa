/* File: generic.h
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

#ifndef __OP_GENERIC_H_
#define __OP_GENERIC_H_

#include <string>
#include <vector>

class OutputPlugin {
  protected:
  std::string uri;
  int chunksize;
  int pid_v;
  std::vector<int> pids_a;
  std::vector<int> pids_d;
  std::vector<int> pids_s;
  
  public:
  OutputPlugin( const std::string &uri, int chunksize );
  virtual void set_pids( int Pid_V, std::vector<int> Pids_A, std::vector<int> Pids_D, std::vector<int> Pids_S );
  virtual void process_data( const std::string &data ) = 0;
  virtual void flush() = 0;  
  virtual ~OutputPlugin() { };
};

#endif
