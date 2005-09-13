/* File: dvbdevice.cc
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
#include <sys/types.h>
#include <sys/stat.h>
#include <fcntl.h>

#include "misc.h"
#include "fp_generic.h"
#include "dvb_device.h"

using namespace std;

DvbDevice::DvbDevice( const std::string &adapter,
		      const std::string &channelsfile):
  file_adapter( adapter ), file_channels( channelsfile ),
  fd(-1), recording_id(0), tuner(NULL)
{

  if (file_adapter.empty()) {
    printD( LOG_WARN, "No adapter is set! Please check config file!\n");
  }

  // start temporary tuner
  Tuner tmptuner(file_adapter);
  // read card type
  card_type = tmptuner.get_type_str();
  // load channel list
  vector<channel_t> clist = tmptuner.load_channels( channelsfile );

  printD( LOG_INFO, "channelsfile contains %d entries\n", clist.size() );

  // convert channel list into dvbdevice data structures
  for(unsigned int i=0; i < clist.size(); ++i) {
    bool bouquet_found = false;

    bouquet_channel_t bchan;
    bchan.name = clist[i].name;
    bchan.pid_video = clist[i].vpid;
    bchan.pid_audio = clist[i].apid;

    for(unsigned int t=0; (t < bouquet_list.size()) && (!bouquet_found); ++t) {
      // the next two are most evil: front_param contains a union which is not compared but it should!
      if ((bouquet_list[t].front_param.frequency == clist[i].front_param.frequency) &&
          (bouquet_list[t].front_param.inversion == clist[i].front_param.inversion) &&
	  (bouquet_list[t].sat_no == clist[i].sat_no) &&
	  (bouquet_list[t].tone   == clist[i].tone) &&
	  (bouquet_list[t].pol    == clist[i].pol)) {

	bouquet_found = true;
	bouquet_list[t].channels.push_back( bchan );
	printD( LOG_VERBOSE, "Known bouquet - new channel - name=%s\n", bchan.name.c_str() );
      }
    }
    if (!bouquet_found) {
      bouquet_t bouquet;
      // TODO FIXME check if this bouquet name is unique!
      bouquet.name = string( "bouquet-" ) + to_string( bouquet_list.size() );
      bouquet.front_param = clist[i].front_param;
      bouquet.sat_no      = clist[i].sat_no;
      bouquet.tone        = clist[i].tone;
      bouquet.pol         = clist[i].pol;
      bouquet.channels.push_back( bchan );

      bouquet_list.push_back( bouquet );
      printD( LOG_VERBOSE, "new bouquet - new channel - name=%s\n", bchan.name.c_str() );
    }
  }
  // stop temporary tuner


  // open dvr device if not open
  string fn( file_adapter );
  if (fn[ fn.length() - 1 ] != '/') {
    fn.append("/");
  }
  fn.append("dvr0");  // TODO FIXME use constant here

  printD( LOG_VERBOSE, "trying to open %s\n", fn.c_str() );
  fd = open( fn.c_str(), O_RDONLY);
  if (fd == -1) {
    printD( LOG_ERROR, "open device %s failed! err=%s (%d)\n", fn.c_str(), strerror(errno), errno);
  }
  printD( LOG_VERBOSE, "%s opened successfully\n", fn.c_str() );
}



DvbDevice::~DvbDevice() {
  // close file
  if (fd >= 0) {
    close(fd);
  }

  // close tuner if open
  if (tuner) {
    delete tuner;
    tuner = NULL;
  }
}


bool DvbDevice::get_pids( std::string chan_name,
			  std::vector< int > &video_pids,
			  std::vector< int > &audio_pids,
			  std::vector< int > &ac3_pids,
			  std::vector< int > &teletext_pids,
			  std::vector< int > &subtitle_pids )
{
  bool found = false;
  // check every bouquet
  for(unsigned int ib=0; ib < bouquet_list.size() && !found; ++ib) {
    // check every channel
    for(unsigned int ic=0; ic < bouquet_list[ib].channels.size() && !found; ++ic) {
      // if specified channel was found in bouquet... (only name comparison)
      if (bouquet_list[ib].channels[ic].name == chan_name) {

	// TODO add all pids that are known
	video_pids.push_back( bouquet_list[ib].channels[ic].pid_video );
	audio_pids.push_back( bouquet_list[ib].channels[ic].pid_audio );

	found = true;
      }
    }
  }
  return found;
}


int DvbDevice::start_recording( std::string &chan_name, FilterChain &fchain ) {
  // returns -1 if channel name is unknown

  int id = recording_id++;

  // switch tuner to correct channel
  // ==> find correct bouquet and then call set_bouquet(...)
  bool notfound = true;
  // check every bouquet
  for(unsigned int ib=0; ib < bouquet_list.size() && notfound; ++ib) {
    // check every channel
    for(unsigned int ic=0; ic < bouquet_list[ib].channels.size() && notfound; ++ic) {
      // if specified channel was found in bouquet... (only name comparison)
      if (bouquet_list[ib].channels[ic].name == chan_name) {

	// instantiate tuner object if it doesn't exist
	if (!tuner) {
	  tuner = new Tuner( file_adapter );
	}

	// ...set tuner to this bouquet and stop search
	tuner->set_bouquet( bouquet_list[ib] );

	// check requested pids
	for(unsigned int i=0; i < fchain.pids.size(); ++i) {
	  // add pids to tuner
	  tuner->add_pid( fchain.pids[i] );
	  // remember pids
	  id2pid[ id ].push_back( fchain.pids[i] );
	}

	notfound = false;
      }
    }
  }
  if (notfound) {
    printD( LOG_ERROR, "BUG: could not find requested bouquet for channel name='%s'!\n",
	    chan_name.c_str() );
    return -1;
  }

  return id;

  // if tuner does not exist then create one
  // search for channel and pids
  // open fd_dvr and register to libnotifier
  // search chan_name in bouquet_list and check, if tuning is neccessary ==> then tune ==> otherwise don't
  // add pids to tuner
  // return id of filter
}


void DvbDevice::stop_recording( int id ) {
  // check if recording id is in id2pid
  if (id2pid.find(id) == id2pid.end()) {
    printD( LOG_WARN, "cannot stop recording with id=%d because it does not exist!\n", id );

  } else {

    // remove pid from tuner
    for(unsigned int i=0; i < id2pid[id].size(); ++i) {
      tuner->remove_pid( id2pid[id][i] );
    }

    // remove id from id2pid
    id2pid.erase( id2pid.find(id) );

    // if no recording is active then close fd_dvr and remove tuner
    if (id2pid.empty()) {
      delete tuner;
      tuner = NULL;
    }
  }
}


const std::vector<bouquet_t> &DvbDevice::get_bouquet_list() const {
  return bouquet_list;
}


const std::string DvbDevice::get_card_type() const {
  return card_type;
}


