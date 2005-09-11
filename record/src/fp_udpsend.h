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

#ifndef __FP_UDPSEND_H_
#define __FP_UDPSEND_H_

#include <Python.h>
#include <sys/socket.h>
#include <netinet/in.h>
#include <arpa/inet.h>
#include <netdb.h>

#include <vector>
#include <string>
#include "fp_generic.h"

class FPUDPSend : public FilterPlugin {
  public:

  FPUDPSend( const std::string &targethost );  // "a.b.c.d:port" or "fqdn:port"
  ~FPUDPSend();

  void add_data( const std::string &data );
  void process_data();
  std::string get_data();

  private:
  int file_fd;             // opened chunk file 

  std::string buffer;      // buffer for caching data
  
  sockaddr_in sockAddrTarget;

  void open_fd( const std::string &targethost );

  sockaddr_in convertStringToSockaddrIn( const std::string addr );
};

PyObject *PyFilter_UDPSend(PyObject *self, PyObject* args);

#endif
