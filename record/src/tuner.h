/* File: tuner.h
 *
 * Author: Sönke Schwardt <schwardt@tzi.de>
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

#ifndef __TUNER_H_
#define __TUNER_H_


#define BUFSIZE 4096

#define NOPID 0xffff

#include <Python.h>
#include <vector>
#include <map>
#include <string>
#include <stdint.h>

#include "frontend.h"
#include "dmx.h"


typedef struct {
  std::string      name;
  int              pid_video;
  int              pid_audio;
} bouquet_channel_t;


// every bouquet_t needs an unique identifier (name)
// if name is empty, this bouquet_t is not valid 
typedef struct {
  std::string                      name;
  struct dvb_frontend_parameters   front_param;
  int                              sat_no;
  int                              tone;
  int                              pol;
  std::vector< bouquet_channel_t > channels;
} bouquet_t;


typedef struct {
  char                            *name;
  struct dvb_frontend_parameters   front_param;
  int                              vpid;
  int                              apid;
  int                              sat_no;
  int                              tone;
  int                              pol;
} channel_t;


typedef struct {
  char *name;
  int value;
} Param;


class Tuner {
  private:
  static const Param inversion_list[];
  static const Param bw_list[];
  static const Param fec_list[];
  static const Param guard_list[];
  static const Param hierarchy_list[];
  static const Param qam_list[];
  static const Param transmissionmode_list[];

  PyObject                       *timer;
  std::string                    device_frontend;
  std::string                    device_demux;
  std::string                    device_dvr;
  int                            fd_frontend;
/*   int                            fd_demuxa, fd_demuxv; */
  std::map<int,int>              map_pid_fd;           // maps pid to demux fd
  std::map<int,int>              map_pid_cnt;          // pid usecount
  struct dvb_frontend_info       feinfo;
  struct dmx_pes_filter_params   pesFilterParamsV;
  struct dmx_pes_filter_params   pesFilterParamsA;
  std::vector<struct dmx_pes_filter_params>   pesFilterParamsM; 
  bouquet_t                      current_bouquet;

  int init_tuner();
  void release_tuner();

  void set_other_pid(int fd, uint16_t pid);

  int set_diseqc(bouquet_t &bouquet);
  int tune_it(struct dvb_frontend_parameters &front_param);

  int find_param(const Param *list, const char *name);
  int extract_channel_from_string(channel_t &channel, char *str, fe_type_t fe_type);

  public:

  Tuner( std::string adapter, PyObject *timer );
  ~Tuner();

  std::string get_type_str() const;

  int set_bouquet(bouquet_t &bouquet);

  int add_pid( int pid );
  int remove_pid( int pid );

  bool timer_expired();
  
  std::vector<channel_t> load_channels( const std::string &channelsfile );
};


#endif
