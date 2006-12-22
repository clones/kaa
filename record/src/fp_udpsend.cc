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
#include "fp_udpsend.h"

using namespace std;

FPUDPSend::FPUDPSend( const std::string &targethost ) :
  file_fd(-1)
{
  open_fd( targethost );
}


FPUDPSend::~FPUDPSend() {
  // flush buffer
  process_data();
  // close file
  if (file_fd >= 0) {
    close(file_fd);
  }
}


void FPUDPSend::add_data( const std::string &data ) {
  buffer.append( data );
}


void FPUDPSend::process_data() {

  // flush data to disk if file is open
  if (file_fd >= 0) {

    while( buffer.size() > 0) {
      int len = (buffer.size() > 1400) ? 1400 : buffer.size();

      if ( sendto(file_fd, buffer.c_str(), len, 0, (sockaddr*)&sockAddrTarget, sizeof(sockaddr_in) ) < 0 ) {
	cerr << "sendPacket: sendto() failed" << endl;
      }

//       int len = write( file_fd, buffer.c_str(), buffer.size() );
//       if (len < 0) {
// 	printD( LOG_ERROR, "failed to write to chunk   fd=%d   errno=%d (%s)\n",
// 		file_fd, errno, strerror(errno) );
//       } else {
	buffer.erase(0, len);
//       }
    }
  }
}


std::string FPUDPSend::get_data()
{
  return "";
}


void FPUDPSend::open_fd( const std::string &targethost ) {

  if (file_fd >= 0) {
    close(file_fd);
  }

  printD( LOG_DEBUG_OUTPUTPLUGIN, "targethost: %s\n", targethost.c_str() );

  // create udp socket
  file_fd = socket(PF_INET, SOCK_DGRAM, IPPROTO_UDP);

  sockAddrTarget = convertStringToSockaddrIn( targethost );

  if (IN_MULTICAST(sockAddrTarget.sin_addr.s_addr)) {
    sockaddr_in iface;
    memset(&iface, 0, sizeof(iface));
    iface.sin_family = AF_INET;

    sockaddr_in sockAddr;
    memset(&sockAddr, 0, sizeof(sockAddr));
    sockAddr.sin_family = AF_INET;
    sockAddr.sin_port = sockAddrTarget.sin_port;
    sockAddr.sin_addr.s_addr = sockAddrTarget.sin_addr.s_addr;

    // reuse port
    int on = 1;
    if ( setsockopt(file_fd, SOL_SOCKET, SO_REUSEADDR, &on, sizeof(on)) != 0 ) {
      printD( LOG_ERROR, "can't reuse address/ports (%s)\n", targethost.c_str() );
    }

    // bind()
    if ( bind(file_fd, (struct sockaddr*)&sockAddr, sizeof(sockAddr)) != 0 ) {
      printD( LOG_ERROR, "bind() failed (%s)\n", targethost.c_str() );
      return;
    }

    // add mc membership
    ip_mreq ipMreq;
    ipMreq.imr_multiaddr = sockAddrTarget.sin_addr;
    ipMreq.imr_interface.s_addr = iface.sin_addr.s_addr;
    if ( setsockopt(file_fd, IPPROTO_IP, IP_ADD_MEMBERSHIP, &ipMreq, sizeof(ipMreq)) != 0 ) {
      printD( LOG_ERROR, "joining multicast group failed (%s)\n", strerror(errno) );
      return;
    }

    // turn on local mc loopback
    on = 1;
    if (setsockopt(file_fd, IPPROTO_IP, IP_MULTICAST_LOOP, &on, sizeof(on)) < 0) {
      printD( LOG_ERROR, "loop setsockopt failed\n" );
      return;
    }
  }
}


sockaddr_in FPUDPSend::convertStringToSockaddrIn( const std::string addr ) {

  // fill struct with address and port
  struct sockaddr_in ucaddr;
  memset((char *) &ucaddr, 0, sizeof(ucaddr));
  ucaddr.sin_family      = AF_INET;
  ucaddr.sin_addr.s_addr = INADDR_ANY;
  ucaddr.sin_port        = 0;

  //****************************************

  // separate host and port
  unsigned int portPos = addr.find_last_of(':');
  if (portPos == string::npos) {
    portPos = addr.find_last_of('/');
  }
  if (portPos == string::npos) {
    printD( LOG_ERROR, "malformed address! ('%s')\n", addr.c_str() );
    return ucaddr;
  }
  // Ist kein Host angegeben, gehen wir von Localhost aus
  string host;
  if (portPos != 0) {
    host = addr.substr(0, portPos);
  } else {
    printD( LOG_ERROR, "no host given!\n" );
    return ucaddr;
  }
  string port = addr.substr(portPos+1, addr.size()-portPos+1);

  printD( LOG_DEBUG_OUTPUTPLUGIN, "host: %s   port: %s\n", host.c_str(), port.c_str() );

  //****************************************

  // resolve names
  addrinfo addrInfoHints;
  addrInfoHints.ai_flags = 0;
  addrInfoHints.ai_family = PF_INET;
  addrInfoHints.ai_socktype = SOCK_DGRAM;
  addrInfoHints.ai_protocol = IPPROTO_UDP;

  addrinfo* addrInfoResult;

  // resolve hostname/ip and port
  if (int r = getaddrinfo(host.c_str(), port.c_str(), &addrInfoHints, &addrInfoResult)) {
    printD( LOG_ERROR, "ERROR(getaddrinfo): %s\n", gai_strerror(r) );
  } else {
    // use only first address
    ucaddr.sin_addr = ((sockaddr_in*)(addrInfoResult->ai_addr))->sin_addr;
    ucaddr.sin_port = ((sockaddr_in*)(addrInfoResult->ai_addr))->sin_port;

    printD( LOG_DEBUG_OUTPUTPLUGIN, "result: host: %s   port: %d\n",
	    inet_ntoa(ucaddr.sin_addr), ntohs(ucaddr.sin_port) );
  }

  return ucaddr;
}


/* Python interface */

PyObject *PyFilter_UDPSend(PyObject *self, PyObject* args)
{
    char *addr;
    
    if (!PyArg_ParseTuple(args,"s", &addr))
	return NULL;

    FPUDPSend *filter = new FPUDPSend(addr);
    return PyCObject_FromVoidPtr((void*) filter, NULL);
}
