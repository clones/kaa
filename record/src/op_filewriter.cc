/* File: op_filewriter.cc
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

#include <cerrno>

// open()
#include <sys/types.h>
#include <sys/stat.h>
#include <fcntl.h>

#include "misc.h"
#include "op_filewriter.h"

using namespace std;

OutputPluginFilewriter::OutputPluginFilewriter( const std::string &uri, int chunksize, FileType ftype ) :
  OutputPlugin(uri, chunksize), file_fd(-1), file_size(0), file_maxsize(chunksize), file_counter(0),
  file_size_total(0), file_name(uri), file_type(ftype), remux(NULL)
{

  printD( LOG_DEBUG_OUTPUTPLUGIN, "URI      : %s\n", uri.c_str() );
  printD( LOG_DEBUG_OUTPUTPLUGIN, "file_name: %s\n", file_name.c_str() );
  printD( LOG_DEBUG_OUTPUTPLUGIN, "maxsize  : %d Bytes\n", file_maxsize );
  printD( LOG_DEBUG_OUTPUTPLUGIN, "file_type: %s\n",
	  ( file_type == FT_RAW ? "RAW" : ( file_type == FT_MPEG ? "MPEG" : "unknown" ) ) );

  buffer_in.reserve(DEFAULT_MAX_BUFFERSIZE);
  buffer_out.reserve(DEFAULT_MAX_BUFFERSIZE);

  open_new_chunk();
}


void OutputPluginFilewriter::set_pids( int Pid_V, std::vector<int> Pids_A,
				       std::vector<int> Pids_D, std::vector<int> Pids_S ) {
  // FIXME TODO
  //   cRemux(VPid, APids, Setup.UseDolbyDigital ? DPids : NULL, SPids, true);

  // call super class
  OutputPlugin::set_pids( Pid_V, Pids_A, Pids_D, Pids_S );

  if (file_type == FT_MPEG) {
    int* p_a = NULL;
    int* p_d = NULL;
    int* p_s = NULL;

    if (pids_a.size()) {
      p_a = new int[ pids_a.size() + 1 ];
      for(unsigned int i = 0; i < pids_a.size(); ++i) {
	p_a[i] = pids_a[i];
      }
      p_a[pids_a.size()] = 0;
    }

    if (pids_d.size()) {
      p_d = new int[ pids_d.size() + 1 ];
      for(unsigned int i = 0; i < pids_d.size(); ++i) {
	p_d[i] = pids_d[i];
      }
      p_d[pids_d.size()] = 0;
    }

    if (pids_s.size()) {
      p_s = new int[ pids_s.size() + 1 ];
      for(unsigned int i = 0; i < pids_s.size(); ++i) {
	p_s[i] = pids_s[i];
      }
      p_s[pids_s.size()] = 0;
    }

    remux = new cRemux( pid_v, p_a, p_d, p_s, false );

    if (p_a) {
      delete[] p_a;
    }

    if (!remux) {
      printD( LOG_ERROR, "ERROR: couldn't allocate memory for remuxer\n");
    }
  }
}


void OutputPluginFilewriter::process_data( const std::string &data ) {
  // append data to buffer
  if (file_type == FT_MPEG) {
    // FT_MPEG
    buffer_in.append( data );
  } else {
    // FT_RAW and others
    buffer_out.append( data );
  }
}


void OutputPluginFilewriter::flush() {
  unsigned char picture_type = NO_PICTURE;

  // if output format IS NOT MPEG ==> TS
  if (file_type != FT_MPEG) {

    // copy in buffer to outbuffer
    buffer_out = buffer_in;
    buffer_in.clear();

  } else {
    // if output format is MPEG

    // add new data to remuxer
    if (buffer_in.size()) {
      int count = remux->Put( (const unsigned char*)buffer_in.c_str(), buffer_in.size() );
      if (count) {
	buffer_in.erase(0, count);
      }
    }

    while(1) {
      int count;
      // get
      unsigned char *p = remux->Get(count, &picture_type);

      // if bufout == NULL ==> not enough data in buffer_in or trash at top of buffer_in
      if (p) {
	// enough data present
	if (picture_type != NO_PICTURE) {
	  // TODO FIXME
	  // processed buffer contained a I/P/B-Frame
	  // 	  if (index && pictureType != NO_PICTURE)
	  // 	    index->Write(pictureType, fileName->Number(), fileSize);
	  //    fileSize += Count;
	  // printD( LOG_DEBUG_OUTPUTPLUGIN, "Frametype %d at filepos %d\n", picture_type, file_size_total);
	}
	// append data to output buffer
	buffer_out.append( (char*)p, count );
	remux->Del(count);
      } else {
	break;
      }
    }
  }


  // flush data to disk if file is open
  if (buffer_out.size() > 0) {

    if (file_fd >= 0) {
      int len = write( file_fd, buffer_out.c_str(), buffer_out.size() );
      if (len < 0) {
	printD( LOG_ERROR, "failed to write to chunk   fd=%d   errno=%d (%s)\n",
		file_fd, errno, strerror(errno) );
      } else {
	buffer_out.erase(0, len);
	file_size += len;
	file_size_total += len;
      }

      if ((file_maxsize > 0) && (file_size > file_maxsize)) {
	open_new_chunk();
      }
    }
  }
}


void OutputPluginFilewriter::open_new_chunk() {

  if (file_fd >= 0) {
    close(file_fd);
  }

  file_size = 0;

  char fnbuf[10];
  string fn(file_name);

  // add counter to filename of second, third, ... chunk
  if (file_counter > 0) {
    sprintf(fnbuf, ".%04d", file_counter);
    fn.append( fnbuf, 5 );
  }

  file_fd = open( fn.c_str(), O_WRONLY | O_CREAT | O_TRUNC | O_LARGEFILE, 0660 );

  if (file_fd < 0) {
    printD( LOG_ERROR, "failed to open chunk '%s'   fd=%d   errno=%d (%s)\n",
	    fn.c_str(), file_fd, errno, strerror(errno) );
  } else {
    printD( LOG_DEBUG_OUTPUTPLUGIN, "chunk opened '%s'  fd=%d\n",
	    fn.c_str(), file_fd );
  }

  file_counter++;
}


OutputPluginFilewriter::~OutputPluginFilewriter() {
  // flush buffer
  flush();
  // close file
  if (file_fd >= 0) {
    close(file_fd);
  }
  if (remux) {
    delete remux;
  }
}
