/* File: tuner.cc
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

// open
#include <sys/types.h>
#include <sys/stat.h>
#include <fcntl.h>
// close
#include <unistd.h>
// ioctl
#include <sys/ioctl.h>

// strerror
#include <cerrno>

#include <vector>
#include <iostream>
#include <stdexcept>

// #include <linux/dvb/frontend.h>
// #include <linux/dvb/dmx.h>

#include "misc.h"
#include "tuner.h"

using namespace std;

const Param Tuner::inversion_list [] = {
	{ "INVERSION_OFF", INVERSION_OFF },
	{ "INVERSION_ON", INVERSION_ON },
	{ "INVERSION_AUTO", INVERSION_AUTO },
        { NULL, 0 }
};

const Param Tuner::bw_list[] = {
	{ "BANDWIDTH_6_MHZ", BANDWIDTH_6_MHZ },
	{ "BANDWIDTH_7_MHZ", BANDWIDTH_7_MHZ },
	{ "BANDWIDTH_8_MHZ", BANDWIDTH_8_MHZ },
        { NULL, 0 }
};

const Param Tuner::fec_list[] = {
	{ "FEC_1_2", FEC_1_2 },
	{ "FEC_2_3", FEC_2_3 },
	{ "FEC_3_4", FEC_3_4 },
	{ "FEC_4_5", FEC_4_5 },
	{ "FEC_5_6", FEC_5_6 },
	{ "FEC_6_7", FEC_6_7 },
	{ "FEC_7_8", FEC_7_8 },
	{ "FEC_8_9", FEC_8_9 },
	{ "FEC_AUTO", FEC_AUTO },
	{ "FEC_NONE", FEC_NONE },
        { NULL, 0 }
};

const Param Tuner::guard_list[] = {
	{"GUARD_INTERVAL_1_16", GUARD_INTERVAL_1_16},
	{"GUARD_INTERVAL_1_32", GUARD_INTERVAL_1_32},
	{"GUARD_INTERVAL_1_4", GUARD_INTERVAL_1_4},
	{"GUARD_INTERVAL_1_8", GUARD_INTERVAL_1_8},
        { NULL, 0 }
};

const Param Tuner::hierarchy_list[] = {
	{ "HIERARCHY_1", HIERARCHY_1 },
	{ "HIERARCHY_2", HIERARCHY_2 },
	{ "HIERARCHY_4", HIERARCHY_4 },
	{ "HIERARCHY_NONE", HIERARCHY_NONE },
        { NULL, 0 }
};

const Param Tuner::qam_list[] = {
	{ "QPSK", QPSK },
	{ "QAM_128", QAM_128 },
	{ "QAM_16", QAM_16 },
	{ "QAM_256", QAM_256 },
	{ "QAM_32", QAM_32 },
	{ "QAM_64", QAM_64 },
        { NULL, 0 }
};

const Param Tuner::transmissionmode_list[] = {
	{ "TRANSMISSION_MODE_2K", TRANSMISSION_MODE_2K },
	{ "TRANSMISSION_MODE_8K", TRANSMISSION_MODE_8K },
        { NULL, 0 }
};



Tuner::Tuner( string adapter ) :
  fd_frontend(-1)
{
  current_bouquet.name = "";  // invalidate current_bouquet (see dvbdevice.h)

  if (adapter.empty()) {
    adapter = "/dev/dvb/adapter0";
  }

  device_frontend = adapter + "/frontend0";
  device_demux    = adapter + "/demux0";
  device_dvr      = adapter + "/dvr0";

  init_tuner();
}


Tuner::~Tuner() {
  release_tuner();
}


int Tuner::init_tuner() {

  release_tuner();

  fd_frontend = -1;

  printD( LOG_INFO, "Opening frontend device\n");
  if ((fd_frontend = open(device_frontend.c_str(), O_RDWR)) < 0){
    printD( LOG_ERROR, "FRONTEND DEVICE: %s\n", strerror(errno));
    release_tuner();
    return -1;
  }

  printD( LOG_INFO, "ioctl(FE_GET_INFO)\n");
  if ((ioctl(fd_frontend, FE_GET_INFO, &feinfo)) < 0) {
    printD( LOG_ERROR, "FE_GET_INFO: %s\n", strerror(errno));
    release_tuner();
    return -1;
  }

  printD( LOG_INFO, "FE_GET_INFO: fe_info.type=%d  (%s)\n",
	  feinfo.type,
	  get_type_str().c_str() );

  printD( LOG_DEBUG_TUNER, "init_tuner was successful\n");
  return 0;
}


void Tuner::release_tuner() {
  if (fd_frontend >= 0) {
    close(fd_frontend);
    fd_frontend = -1;
  }
}


void Tuner::set_other_pid(int fd, uint16_t pid) {

  if (pid==NOPID || pid==0x1fff) {
    printD( LOG_DEBUG_TUNER, "ioctl(fd_demuxv, DMX_STOP)\n");
    ioctl(fd, DMX_STOP);
    return;
  }

  struct dmx_pes_filter_params M;

  M.pid      = pid;
  M.input    = DMX_IN_FRONTEND;
  M.output   = DMX_OUT_TS_TAP;
  M.pes_type = DMX_PES_OTHER;
  M.flags    = DMX_IMMEDIATE_START;
  pesFilterParamsM.push_back(M);

  printD( LOG_DEBUG_TUNER, "ioctl(fd_miscX, DMX_SET_PES_FILTER)   fd=%d   pid=%d\n", fd, pid);
  if (ioctl(fd, DMX_SET_PES_FILTER, &M) < 0) {
    printD( LOG_ERROR, "ioctl failed: %s\n", strerror(errno));
  }
}

int Tuner::set_diseqc(bouquet_t &bouquet) {

  // returns 0 on success and -1 on failure

  struct dvb_diseqc_master_cmd cmd = {{0xe0, 0x10, 0x38, 0xf0, 0x00, 0x00}, 4};

  printD( 8, "entering  (chan.name=%s)\n", bouquet.name.c_str());

  cmd.msg[3] = 0xf0 | ((bouquet.sat_no * 4) & 0x0f) | (bouquet.tone ? 1 : 0) | (bouquet.pol ? 0 : 2);

  if (ioctl(fd_frontend, FE_SET_TONE, SEC_TONE_OFF) < 0) {
    printD( LOG_ERROR, "FE_SET_TONE: failed\n");
    return -1;
  }

  if (ioctl(fd_frontend, FE_SET_VOLTAGE, bouquet.pol ? SEC_VOLTAGE_13 : SEC_VOLTAGE_18) < 0) {
    printD( LOG_ERROR, "FE_SET_VOLTAGE: failed\n");
    return -1;
  }

  usleep(15000);
  if (ioctl(fd_frontend, FE_DISEQC_SEND_MASTER_CMD, &cmd) < 0) {
    printD( LOG_ERROR, "FE_DISEQC_SEND_MASTER_CMD: failed\n");
    return -1;
  }

  usleep(15000);
  if (ioctl(fd_frontend, FE_DISEQC_SEND_BURST, (bouquet.sat_no / 4) % 2 ? SEC_MINI_B : SEC_MINI_A) < 0) {
    printD( LOG_ERROR, "FE_DISEQC_SEND_BURST: failed\n");
    return -1;
  }

  usleep(15000);
  if (ioctl(fd_frontend, FE_SET_TONE, bouquet.tone ? SEC_TONE_ON : SEC_TONE_OFF) < 0) {
    printD( LOG_ERROR, "FE_SET_TONE: failed\n");
    return -1;
  }

   return 0;
}


int Tuner::tune_it (struct dvb_frontend_parameters &front_param) {

  // returns 0 on success and -1 on failure

  fe_status_t status;

  printD( LOG_DEBUG_TUNER, "front_param.frequency          = %d\n", front_param.frequency);
  printD( LOG_DEBUG_TUNER, "front_param.inversion          = %d\n", front_param.inversion);
  printD( LOG_DEBUG_TUNER, "front_param.ofdm.bandwidth     = %d\n", front_param.u.ofdm.bandwidth );
  printD( LOG_DEBUG_TUNER, "front_param.ofdm.code_rate_HP  = %d\n", front_param.u.ofdm.code_rate_HP );
  printD( LOG_DEBUG_TUNER, "front_param.ofdm.code_rate_LP  = %d\n", front_param.u.ofdm.code_rate_LP );
  printD( LOG_DEBUG_TUNER, "front_param.ofdm.constellation = %d\n", front_param.u.ofdm.constellation );
  printD( LOG_DEBUG_TUNER, "front_param.ofdm.transmission_m= %d\n", front_param.u.ofdm.transmission_mode );
  printD( LOG_DEBUG_TUNER, "front_param.ofdm.guard_interval= %d\n", front_param.u.ofdm.guard_interval );
  printD( LOG_DEBUG_TUNER, "front_param.ofdm.hierarchy_info= %d\n", front_param.u.ofdm.hierarchy_information );

  if (ioctl(fd_frontend, FE_SET_FRONTEND, &front_param) < 0) {
    printD( LOG_ERROR, "setfront front: %s\n", strerror(errno));
  }

  do {
    if (ioctl(fd_frontend, FE_READ_STATUS, &status) < 0) {
      printD( LOG_ERROR, "fe get event: %s\n", strerror(errno));
      return -1;
    }

    printD( LOG_DEBUG_TUNER,
	    "input_dvb: status: 0x%04x  |%s|%s|%s|%s|%s|%s|\n", status,
	    (status & FE_HAS_SIGNAL ? "FE_HAS_SIGNAL" : "             "),
	    (status & FE_TIMEDOUT   ? "FE_TIMEDOUT"   : "           "),
	    (status & FE_HAS_LOCK   ? "FE_HAS_LOCK"   : "           "),
	    (status & FE_HAS_CARRIER? "FE_HAS_CARRIER": "              "),
	    (status & FE_HAS_VITERBI? "FE_HAS_VITERBI": "              "),
	    (status & FE_HAS_SYNC   ? "FE_HAS_SYNC"   : "           ")
	    );

    if (status & FE_HAS_LOCK) {
      return 0;
    }
    usleep(50000);
  }
  while (!(status & FE_TIMEDOUT));

  return -1;
}


int Tuner::add_pid( int pid ) {

  // returns 0 on success and -1 on failure

  printD( LOG_DEBUG_TUNER, "registering pid=%d\n", pid );

  if (map_pid_fd.find(pid) == map_pid_fd.end()) {

    printD( LOG_INFO, "Opening demux device: %s\n", device_demux.c_str() );
    int fd = open(device_demux.c_str(), O_RDWR);

    if (fd < 0) {

      printD( LOG_ERROR, "open demux device failed: %s\n", strerror(errno));
      return -1;

    } else {

      map_pid_cnt[ pid ] = 1;
      map_pid_fd[ pid ] = fd;
      set_other_pid(fd, pid);

    }
  } else {
    ++map_pid_cnt[ pid ];
  }

  return 0;
}


int Tuner::remove_pid( int pid ) {

  // returns 0 on success and -1 on failure

  printD( LOG_DEBUG_TUNER, "removing pid=%d\n", pid );

  if (map_pid_fd.find(pid) == map_pid_fd.end()) {

    printD( LOG_WARN, "pid %d was not registered!\n", pid );
    return -1;

  } else {

    // decrease usecount
    --map_pid_cnt[ pid ];
    if (map_pid_cnt[ pid ] < 1) {
      // pid not used anymore
      set_other_pid(map_pid_fd[pid], NOPID);
      close(map_pid_fd[pid]);
      map_pid_fd.erase( pid );
      map_pid_cnt[ pid ] = 0;
    }
  }

  return 0;
}


int Tuner::set_bouquet( bouquet_t &bouquet ) {

  // returns 0 on success and -1 on failure

  printD( LOG_DEBUG_TUNER, "bouquet.name='%s'  freq=%d  satno=%d  tone=%d   pol=%d\n",
	  bouquet.name.c_str(),
	  bouquet.front_param.frequency,
	  bouquet.sat_no,
	  bouquet.tone,
	  bouquet.pol
	  );

  if ( bouquet.name != current_bouquet.name ) {
    current_bouquet = bouquet;
  } else {
    // tuner is already tuned to correct bouquet
    return 0;
  }

  //   remove_pid( 0x00 ); // PAT
  //   remove_pid( 0x01 ); // CAT
  //   remove_pid( 0x02 ); // TSDT
  //   remove_pid( 0x11 ); // BAT / SDT
  //   remove_pid( 0x12 ); // EIT
  //   remove_pid( 0x13 ); // RST
  //   remove_pid( 0x14 ); // TOT / TDT
  //   remove_pid( 0x1E ); // DIT
  //   remove_pid( 0x1F ); // SIT

  if (feinfo.type==FE_QPSK) {
    if (set_diseqc(current_bouquet) < 0) {
      return -1;
    }
  }

  printD( LOG_DEBUG_TUNER, "calling tune_it\n");

  if (tune_it(current_bouquet.front_param) < 0) {
    return -1;
  }

  //   add_pid( 0x00 ); // PAT
  //   add_pid( 0x01 ); // CAT
  //   add_pid( 0x02 ); // TSDT
  //   add_pid( 0x11 ); // BAT / SDT
  //   add_pid( 0x12 ); // EIT
  //   add_pid( 0x13 ); // RST
  //   add_pid( 0x14 ); // TOT / TDT
  //   add_pid( 0x1E ); // DIT
  //   add_pid( 0x1F ); // SIT

  return 0;
}


int Tuner::find_param(const Param *list, const char *name)
{
  while (list->name && strcmp(list->name, name))
    list++;
  return list->value;;
}


int Tuner::extract_channel_from_string(channel_t &channel, char *str, fe_type_t fe_type)
{
  /*
    try to extract channel data from a string in the following format
    (DVBS) QPSK: <channel name>:<frequency>:<polarisation>:<sat_no>:<sym_rate>:<vpid>:<apid>
    (DVBC) QAM:  <channel name>:<frequency>:<inversion>:<sym_rate>:<fec>:<qam>:<vpid>:<apid>
    (DVBT) OFDM: <channel name>:<frequency>:<inversion>:<bw>:<fec_hp>:<fec_lp>:<qam>:
	 			<transmissionm>:<guardlist>:<hierarchinfo>:<vpid>:<apid>

    <channel name> = any string not containing ':'
    <frequency>    = unsigned long
    <polarisation> = 'v' or 'h'
    <sat_no>       = unsigned long, usually 0 :D
    <sym_rate>     = symbol rate in MSyms/sec


    <inversion>    = INVERSION_ON | INVERSION_OFF | INVERSION_AUTO
    <fec>          = FEC_1_2, FEC_2_3, FEC_3_4 .... FEC_AUTO ... FEC_NONE
    <qam>          = QPSK, QAM_128, QAM_16 ...

    <bw>           = BANDWIDTH_6_MHZ, BANDWIDTH_7_MHZ, BANDWIDTH_8_MHZ
    <fec_hp>       = <fec>
    <fec_lp>       = <fec>
    <transmissionm> = TRANSMISSION_MODE_2K, TRANSMISSION_MODE_8K
    <vpid>         = video program id
    <apid>         = audio program id

  */
  unsigned long freq;
  char *field, *tmp;
  tmp = str;

  /* find the channel name */
  if(!(field = strsep(&tmp,":")))return -1;
  channel.name = strdup(field);

  /* find the frequency */
  if(!(field = strsep(&tmp, ":")))return -1;
  freq = strtoul(field,NULL,0);

  switch(fe_type)
    {
    case FE_QPSK:
      if(freq > 11700)
	{
	  channel.front_param.frequency = (freq - 10600)*1000;
	  channel.tone = 1;
	} else {
	  channel.front_param.frequency = (freq - 9750)*1000;
	  channel.tone = 0;
	}
      channel.front_param.inversion = INVERSION_OFF;

      /* find out the polarisation */
      if(!(field = strsep(&tmp, ":")))return -1;
      channel.pol = (field[0] == 'h' ? 0 : 1);

      /* satellite number */
      if(!(field = strsep(&tmp, ":")))return -1;
      channel.sat_no = strtoul(field, NULL, 0);

      /* symbol rate */
      if(!(field = strsep(&tmp, ":")))return -1;
      channel.front_param.u.qpsk.symbol_rate = strtoul(field, NULL, 0) * 1000;

      channel.front_param.u.qpsk.fec_inner = FEC_AUTO;
      break;
    case FE_QAM:
      channel.front_param.frequency = freq;

      /* find out the inversion */
      if(!(field = strsep(&tmp, ":")))return -1;
      channel.front_param.inversion = (fe_spectral_inversion_t)find_param(inversion_list, field);

      /* find out the symbol rate */
      if(!(field = strsep(&tmp, ":")))return -1;
      channel.front_param.u.qam.symbol_rate = strtoul(field, NULL, 0);

      /* find out the fec */
      if(!(field = strsep(&tmp, ":")))return -1;
      channel.front_param.u.qam.fec_inner = (fe_code_rate_t)find_param(fec_list, field);

      /* find out the qam */
      if(!(field = strsep(&tmp, ":")))return -1;
      channel.front_param.u.qam.modulation = (fe_modulation_t)find_param(qam_list, field);
      break;
    case FE_OFDM:
      channel.front_param.frequency = freq;

      /* find out the inversion */
      if(!(field = strsep(&tmp, ":")))return -1;
      channel.front_param.inversion = (fe_spectral_inversion_t)find_param(inversion_list, field);

      /* find out the bandwidth */
      if(!(field = strsep(&tmp, ":")))return -1;
      channel.front_param.u.ofdm.bandwidth = (fe_bandwidth_t)find_param(bw_list, field);

      /* find out the fec_hp */
      if(!(field = strsep(&tmp, ":")))return -1;
      channel.front_param.u.ofdm.code_rate_HP = (fe_code_rate_t)find_param(fec_list, field);

      /* find out the fec_lp */
      if(!(field = strsep(&tmp, ":")))return -1;
      channel.front_param.u.ofdm.code_rate_LP = (fe_code_rate_t)find_param(fec_list, field);

      /* find out the qam */
      if(!(field = strsep(&tmp, ":")))return -1;
      channel.front_param.u.ofdm.constellation = (fe_modulation_t)find_param(qam_list, field);

      /* find out the transmission mode */
      if(!(field = strsep(&tmp, ":")))return -1;
      channel.front_param.u.ofdm.transmission_mode = (fe_transmit_mode_t)find_param(transmissionmode_list, field);

      /* guard list */
      if(!(field = strsep(&tmp, ":")))return -1;
      channel.front_param.u.ofdm.guard_interval = (fe_guard_interval_t)find_param(guard_list, field);

      if(!(field = strsep(&tmp, ":")))return -1;
      channel.front_param.u.ofdm.hierarchy_information = (fe_hierarchy_t)find_param(hierarchy_list, field);
      break;
    }

  if(!(field = strsep(&tmp, ":")))return -1;
  channel.vpid = strtoul(field, NULL, 0);

  if(channel.vpid == 0)return -1; /* only tv channels for now */

  if(!(field = strsep(&tmp, ":")))return -1;
  channel.apid = strtoul(field, NULL, 0);

  return 0;
}


vector<channel_t> Tuner::load_channels( const std::string &channelsfile ) {

  FILE      *f;
  char       str[BUFSIZE];
  vector<channel_t> channels;
  channel_t  channel;
  int        num_channels;

  if (!channelsfile.size()) {
    return channels;
  }

  printD( LOG_INFO, "channelsfile=%s\n", channelsfile.c_str() );

  f = fopen(channelsfile.c_str(), "rb");
  if (!f) {
    printD( LOG_ERROR, "input_dvb: failed to open dvb channel file '%s'\n", channelsfile.c_str());
    return channels;
  }

  /*
   * count and alloc channels
   */
  num_channels = 0;
  while ( fgets (str, BUFSIZE, f)) {
    num_channels++;
  }
  fclose (f);

  if(num_channels > 0)
    printD( LOG_INFO, "input_dvb: expecting %d channels...\n", num_channels);
  else {
    printD( LOG_WARN, "input_dvb: no channels found in the file: giving up.\n");
    return channels;
  }

  /*
   * load channel list
   */

  f = fopen (channelsfile.c_str(), "rb");
  num_channels = 0;
  while ( fgets (str, BUFSIZE, f)) {
    if(extract_channel_from_string( channel, str, feinfo.type) < 0)continue;
    channels.push_back(channel);
    num_channels++;
  }

  if(num_channels > 0)
    printD( LOG_INFO, "input_dvb: found %d channels...\n", num_channels);
  else {
    printD( LOG_WARN, "input_dvb: no channels found in the file: giving up.\n");
    return channels;
  }

  return channels;
}


std::string Tuner::get_type_str() const {
  return (feinfo.type == FE_OFDM ? "DVB-T" :
	  feinfo.type == FE_QAM  ? "DVB-C" :
	  feinfo.type == FE_QPSK ? "DVB-S" : "unknown");
}
