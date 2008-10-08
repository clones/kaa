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
#include "fp_filewriter.h"

using namespace std;

FPFilewriter::FPFilewriter( const std::string &uri, int chunksize ) :
  file_fd(-1), file_size(0), file_maxsize(chunksize), file_counter(0),
  file_size_total(0), file_name(uri)
{

  printD( LOG_DEBUG_OUTPUTPLUGIN, "URI      : %s\n", uri.c_str() );
  printD( LOG_DEBUG_OUTPUTPLUGIN, "file_name: %s\n", file_name.c_str() );
  printD( LOG_DEBUG_OUTPUTPLUGIN, "maxsize  : %d Bytes\n", file_maxsize );

  open_new_chunk();
}


FPFilewriter::~FPFilewriter() {
  // flush buffer
  process_data();
  // close file
  if (file_fd >= 0) {
    close(file_fd);
  }
}


void FPFilewriter::add_data( const std::string &data ) {
  buffer.append( data );
}


void FPFilewriter::process_data() {

  // flush data to disk if file is open
  if (buffer.size() > 0) {

    if (file_fd >= 0) {
      int len = write( file_fd, buffer.c_str(), buffer.size() );
      if (len < 0) {
	printD( LOG_ERROR, "failed to write to chunk   fd=%d   errno=%d (%s)\n",
		file_fd, errno, strerror(errno) );
      } else {
	buffer.erase(0, len);
	file_size += len;
	file_size_total += len;
      }

      if ((file_maxsize > 0) && (file_size > file_maxsize)) {
	open_new_chunk();
      }
    }
  }
}


std::string FPFilewriter::get_data()
{
  return "";
}


void FPFilewriter::open_new_chunk() {

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


/* Python interface */

PyObject *PyFilter_Filewriter(PyObject *self, PyObject* args)
{
    char *fname;
    int chunksize;
    
    if (!PyArg_ParseTuple(args,"si", &fname, &chunksize))
	return NULL;

    FPFilewriter *filter = new FPFilewriter(fname, chunksize);
    return PyCObject_FromVoidPtr((void*) filter, NULL);
}
