/* File: op_generic.cc
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

#include "misc.h"
#include "op_generic.h"

OutputPlugin::OutputPlugin( const std::string &uri, int chunksize ) :
  uri(uri), chunksize(chunksize), pid_v(0)
{
  ;
}

void OutputPlugin::set_pids( int Pid_V, std::vector<int> Pids_A, 
			     std::vector<int> Pids_D, std::vector<int> Pids_S ) {
  pid_v  = Pid_V;
  pids_a = Pids_A;
  pids_d = Pids_D;
  pids_s = Pids_S;
  // TODO FIXME  fix debug output
  //   printD( LOG_DEBUG_OUTPUTPLUGIN, "setting pids: v=%d  a1=%d  a2=%d  d1=%d  d2=%d\n",
  // 	  pid_v, pid_a1, pid_a2, pid_d1, pid_d2 );
}
