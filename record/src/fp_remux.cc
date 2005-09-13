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

#include <Python.h>
#include <cerrno>

// open()
#include <sys/types.h>
#include <sys/stat.h>
#include <fcntl.h>

#include "misc.h"
#include "fp_remux.h"

using namespace std;

FPRemux::FPRemux() : remux(NULL)
{
  buffer_in.reserve(DEFAULT_MAX_BUFFERSIZE);
  buffer_out.reserve(DEFAULT_MAX_BUFFERSIZE);
}


FPRemux::~FPRemux() {
  // flush buffer
  process_data();
  // close file
  if (remux) {
    delete remux;
  }
}


void FPRemux::set_pids( int pid_v,
			std::vector<int> pids_a,
			std::vector<int> pids_d,
			std::vector<int> pids_s )
{
  // FIXME TODO
  //   cRemux(VPid, APids, Setup.UseDolbyDigital ? DPids : NULL, SPids, true);

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
  remux->SetTimeouts(0,0);

  if (p_a) {
    delete[] p_a;
  }
  if (p_d) {
    delete[] p_d;
  }
  if (p_s) {
    delete[] p_s;
  }

  if (!remux) {
    printD( LOG_ERROR, "ERROR: couldn't allocate memory for remuxer\n");
  }
}


void FPRemux::add_data( const std::string &data ) {
  // append data to buffer
  buffer_in.append( data );
}


void FPRemux::process_data() {

  unsigned char picture_type = NO_PICTURE;

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


std::string FPRemux::get_data()
{
  std::string ret(buffer_out);
  buffer_out.erase();
  return ret;
}

/* Python interface */

PyObject *PyFilter_Remux(PyObject *self, PyObject* args)
{
    int vpid;
    int apid;

    // TODO: support other pids
    if (!PyArg_ParseTuple(args,"ii", &vpid, &apid))
	return NULL;

    std::vector<int> pids_a, pids_d, pids_s;
    pids_a.push_back(apid);
    
    FPRemux *filter = new FPRemux();
    filter->set_pids(vpid, pids_a, pids_d, pids_s);
    return PyCObject_FromVoidPtr((void*) filter, NULL);
}
