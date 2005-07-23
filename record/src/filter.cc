/* File: filter.cc
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

#include <set>

#include "misc.h"
#include "op_generic.h"
#include "filter.h"

using namespace std;


Filter::Filter() : idcounter(0) {
  ;
}


Filter::~Filter() {
  // iterate through all registered filters and destroy corresponding output plugin
  std::map<int, FilterData>::iterator iter;
  for( iter = id2filter.begin() ; iter != id2filter.end() ; ++iter) {
    delete iter->second.op;
    iter->second.op = NULL;
  }
}


int Filter::add_filter( FilterData &fdata ) {

  int id = idcounter;
  // register new filter
  id2filter[ id ] = fdata;
  // add output plugin to requested pid
  for(int i=fdata.pids.size()-1; i >= 0 ; --i) {
    pid2op[ fdata.pids[i] ].push_back( fdata.op );
    printD( LOG_DEBUG_FILTER, "Added output filter 0x%p to pid %d\n", fdata.op, fdata.pids[i] );
  }
  // jump to next id :-)
  ++idcounter;

  return id;
}


bool Filter::remove_filter( int id ) {
  // check if filter id does exist
  if ( id2filter.find(id) != id2filter.end() ) {
    // interate every pid for this filter id
    for(unsigned int i = 0; i < id2filter[id].pids.size(); ++i) {
      int pid = id2filter[id].pids[i];
      // iterate through all output plugins which are registered to "pid"
      int size = pid2op[ pid ].size();
      for( int t = size-1; t >= 0; --t ) {
	// if output plugin matches with output plugin of requested filter id
	if ( pid2op[ pid ][t] == id2filter[id].op ) {
	  // then remove it
	  pid2op[ pid ].erase( pid2op[ pid ].begin() + t );
	  printD( LOG_DEBUG_FILTER, "Removed output filter 0x%p from pid %d\n",
		  id2filter[id].op, pid );
	}
      }
    }
    // free output plugin
    delete id2filter[id].op;
    // remove filter id from id2filter
    id2filter.erase( id2filter.find(id) );
    printD( LOG_DEBUG_FILTER, "Removed filter with id %d\n", id );

    return true;
  }

  return false;
}


void Filter::process_data( std::string &data ) {
  // append new data to buffer
  buffer.append( data );
  // new data
  scan_buffer();
}


void Filter::scan_buffer() {

  unsigned int i;

  // should be at least two transport stream frames
  if (buffer.length() < 2*188) {
    printD( LOG_WARN, "not enough data\n");
    return;
  }

  // check if they are really transport stream frames
  for ( i = 0; i < 188 ; i++){
    if (( buffer[i] == 0x47 ) &&
	( buffer[i+188] == 0x47 ))break;
  }
  if ( i == 188){
    printD( LOG_WARN, "not a transport stream\n");
    return;
  } else if (i) {
    printD( LOG_WARN, "dropping %d bytes to get TS in sync\n", i);
    // if unequal 0 then cutoff bogus
    buffer.erase(0,i);
  }

  i = 0;
  int buflen = buffer.size();

  typedef set< OutputPlugin*, greater<OutputPlugin*> > OP_List;
  OP_List op_list;

  // iterate through all complete frames
  while( buflen - i >= 188 ) {

    // check frame
    if (buffer[i] != 0x47) {

      // frame invalid
      printD( LOG_VERBOSE, "invalid ts frame 0x%02x\n", buffer[i] );

    } else {

      // frame ok
      bool ts_error = ((int)(buffer[i+1] & 0x80) >> 7);
      //       bool pusi     = ((int)(buffer[i+1] & 0x40) >> 6);
      //       bool ts_prio  = ((int)(buffer[i+1] & 0x20) >> 5);
      int  pid      = ((((int)buffer[i+1] & 0x1F) << 8) | ((int)buffer[i+2] & 0xFF));
      int  ts_sc    = ((int)(buffer[i+3] & 0xC0) >> 6);
      //       int  afc      = ((int)(buffer[i+3] & 0x30) >> 4);
      //       int  cc       = ((int)(buffer[i+3] & 0x0F));
      // printD( LOG_DEBUG_FILTER,
      //         "offset=%05d  ts_error=%d  pusi=%d  ts_prio=%d  pid=%d  ts_sc=%d  afc=%d  cc=%d\n",
      // 	 i, ts_error, pusi, ts_prio, pid, ts_sc, afc, cc );

      if (ts_error) {
	printD( LOG_DEBUG_FILTER, "ts frame is damaged!\n");
      }
      if (ts_sc) {
	printD( LOG_VERBOSE, "ts frame is scrambled!\n");
      }

      // iterate over all registered output plugins for this pid
      int size = pid2op[ pid ].size();
      for( int plugi = 0; plugi < size; ++plugi ) {
	// pass ts frame to output plugin
	pid2op[ pid ][plugi]->process_data( buffer.substr(i,188) );
	// remember output plugin to call flush() only on those plugins which received data
	op_list.insert( pid2op[ pid ][plugi] );
      }
    }
    // jump to next ts frame
    i += 188;
  }

  buffer.erase(0,i);

  // call flush on all output plugins that received new data
  for( OP_List::iterator iter = op_list.begin(); iter != op_list.end() ; ++iter ) {
    (*iter)->flush();
  }
}

// *************************************************************


/* schaut nach, wie viele Schedulings gerade aktiv sind.
   Wenn ein *neues* Scheduling gefunden wird, werden die entsprechenden PIDs eingetragen
   Wenn ein *altes* Scheduling entfernt wurde, werden die entsprechenden PIDs entfernt
*/
// int Filter::check_scheduled_entries() {
//   printD( 5, "checking for new schedules\n" );

//   int size=config.sched_entries.size();
//   for(int i=0; i < size; ++i) {
//     if ( pid2sched_entry.find( config.sched_entries[i].chan_info.pid_video ) == pid2sched_entry.end() ) {
//       pid2sched_entry[ config.sched_entries[i].chan_info.pid_video ] = &config.sched_entries[i];
//       if (config.devices[devnr].tuner) {
// 	config.devices[devnr].tuner->add_pid( config.sched_entries[i].chan_info.pid_video );
//       }
//       printD( 5, "Adding to filter new video pid: %d\n", config.sched_entries[i].chan_info.pid_video );
//     }
//     if ( pid2sched_entry.find( config.sched_entries[i].chan_info.pid_audio ) == pid2sched_entry.end() ) {
//       pid2sched_entry[ config.sched_entries[i].chan_info.pid_audio ] = &config.sched_entries[i];
//       if (config.devices[devnr].tuner) {
// 	config.devices[devnr].tuner->add_pid( config.sched_entries[i].chan_info.pid_audio );
//       }
//       printD( 5, "Adding to filter new audio pid: %d\n", config.sched_entries[i].chan_info.pid_audio );
//     }
//   }
//   return 0;
// }

// EventResult Filter::whenReadReady(const FD& f)
// {
//   read_data();

//   return OK;
// }


// void Filter::read_data() {

//   static char buf[BUFFERSIZE];

//   int len = read(fd, buf, BUFFERSIZE);
//   if (len<0) {
//     printD( 5, "WARNING: read failed: errno=%d  err=%s\n", errno, strerror(errno) );
//   }
//   if (len>0) {
//     buffer.append( string(buf,len) );
//     // new data
//     scan_buffer();
//   }
// }


/*
bool Filter::add_recorder( output_t &rec ) {

  if (!rec.rec) {
    return false;
  }

  outputs.push_back( rec );
  return true;

}


bool Filter::rm_recorder( std::string channame ) {
  bool found = false;

  for(unsigned int i=0; i < outputs.size(); i++) {
    if (outputs[i].channame == channame) {
      delete( outputs[i].rec );
      outputs.erase( outputs.begin() + i );
      found = true;
      i--;  // extremely evil ==> unsigned int FIXME
    }
  }

  return found;
}

*/
