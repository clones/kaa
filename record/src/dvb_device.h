/* File: dvbdevice.h
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

#ifndef __DVB_DEVICE_H_
#define __DVB_DEVICE_H_

#include <Python.h>
#include "filter.h"
#include "dvb_tuner.h"

class Tuner;

class DvbDevice {
  public:
  static const int BUFFERSIZE = 18800;

  private:

  std::string     file_adapter;                   // path of used adapter (e.g. /dev/dvb/adapter0/)
  std::string     file_channels;                  // path of channel list (e.g. /root/.channels.conf)
  int             priority;
  int             fd;
  std::string     card_type;                      // "DVB-T", "DVB-S", "DVB-C" or "unknown"
  std::vector<bouquet_t> bouquet_list;
  Tuner          *tuner;
  Filter          filter;
  std::map<int, std::vector<int> >  id2pid;       // registered filter
  PyObject       *socket_dispatcher;
  
  public:
  // DvbDevice(...)
  // params: adapter that should be opened (e.g. /dev/dvb/adapter0/)
  // params: channelsfile which contains frequencies etc for given adapter
  // params: prio is the priority for this card
  DvbDevice( const std::string &adapter, const std::string &channelsfile, int prio);

  // destructor()
  ~DvbDevice();

  // start recording immediately
  // param: chan_name is the name of desired channel
  // param: fdata is the filter chain that shall process the data
  // returns: id of this recording (important for stop_recording())
  int start_recording( std::string &chan_name, FilterData &fdata );

  // stop recording immediately
  // param: id of desired recording
  // returns: nothing
  void stop_recording( int id );

  // returns: bouquet list if dvbdevice
  const std::vector<bouquet_t> &get_bouquet_list() const;

  // returns: in card_type type of device ("DVB-T", "DVB-C", "DVB-S" or "unknown")
  const std::string get_card_type() const;

  // set notifier object
  void connect_to_notifier(PyObject* socket_dispatcher);
  
  // callback for notifier
  void read_fd_data();

  // get all relevant pids for given channelname
  bool get_pids( std::string channelname, 
		 std::vector< int > &video_pids,
		 std::vector< int > &audio_pids,
		 std::vector< int > &ac3_pids,
		 std::vector< int > &teletext_pids,
		 std::vector< int > &subtitle_pids );
  
  Filter &get_filter() { return filter; }
};

#endif
