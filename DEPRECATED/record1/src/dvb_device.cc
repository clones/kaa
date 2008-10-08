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
  recording_id(0), tuner(NULL)
{

  if (file_adapter.empty()) {
    printD( LOG_WARN, "No adapter is set! Please check config file!\n");
  }

  // start temporary tuner
  Tuner tmptuner(file_adapter);
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
}



DvbDevice::~DvbDevice() {
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

    // if no recording is active then remove tuner
    if (id2pid.empty()) {
      delete tuner;
      tuner = NULL;
    }
  }
}


const std::vector<bouquet_t> &DvbDevice::get_bouquet_list() const {
  return bouquet_list;
}



/* ********************* PYTHON WRAPPER CODE ************************ */


int debug_level = 65535;

#define DEVICE ((DvbDevicePyObject *)self)->device

typedef struct {
    PyObject_HEAD
    DvbDevice *device;
} DvbDevicePyObject;


static int DvbDevicePyObject__init(DvbDevicePyObject *self, PyObject *args)
{
  char *adapter;
  char *channels;

  if (!PyArg_ParseTuple(args,"ss", &adapter, &channels))
    return -1;

  self->device = new DvbDevice(adapter, channels);
  return 0;
}


void DvbDevicePyObject__dealloc(DvbDevicePyObject *self)
{
    delete self->device;
    PyMem_DEL(self);
}


PyObject *PyFromIntVector(std::vector< int >& v)
{
    PyObject *list = PyList_New(0);
    for (unsigned int i = 0; i < v.size(); i++)
      PyList_Append(list, PyInt_FromLong(v[i]));
    return list;
}


PyObject *DvbDevicePyObject__get_pids(PyObject *self, PyObject* args)
{
    char *channel;
    std::vector< int > video_pids, audio_pids, ac3_pids, teletext_pids, subtitle_pids;

    if (!PyArg_ParseTuple(args, "s", &channel))
	return NULL;

    DEVICE->get_pids(channel, video_pids, audio_pids, ac3_pids, teletext_pids,
		     subtitle_pids );
    PyObject *list = Py_BuildValue("OOOOO", PyFromIntVector(video_pids),
				   PyFromIntVector(audio_pids), PyFromIntVector(ac3_pids),
				   PyFromIntVector(teletext_pids),
				   PyFromIntVector(subtitle_pids));
    return list;
}


PyObject *DvbDevicePyObject__start_recording(PyObject *self, PyObject* args)
{
    int result;
    char *channel;
    std::string channel_str;
    PyObject *plugin_PyObject;
    FilterChain* plugin_pointer;

    if (!PyArg_ParseTuple(args, "sO", &channel, &plugin_PyObject))
	return NULL;

    plugin_pointer = (FilterChain*) PyCObject_AsVoidPtr(plugin_PyObject);

    // create stupid reference
    channel_str = channel;
    result = DEVICE->start_recording(channel_str, *plugin_pointer);

    return Py_BuildValue("i", result);
}


PyObject *DvbDevicePyObject__stop_recording(PyObject *self, PyObject* args)
{
  int id;

  if (!PyArg_ParseTuple(args, "i", &id))
    return NULL;

  DEVICE->stop_recording(id);
  Py_INCREF(Py_None);
  return Py_None;
}


PyObject *DvbDevicePyObject__get_bouquet_list(PyObject *self, PyObject* args)
{
  std::vector<bouquet_t> bouquet_list;
  PyObject *result;

  bouquet_list = DEVICE->get_bouquet_list();
  result = PyList_New(bouquet_list.size());
  for (unsigned int i=0; i<bouquet_list.size(); i++) {
    std::vector< bouquet_channel_t > &channels = bouquet_list[i].channels;
    PyObject *l = PyList_New(channels.size());
    PyList_SetItem(result, i, l);
    for (unsigned int j=0; j<channels.size(); j++) {
      PyObject *c = PyString_FromString(channels[j].name.c_str());
      PyList_SetItem(l, j, c);
    }
  }
  return result;
}


static PyMethodDef DvbDevicePyObject__methods[] = {
    {"get_pids", DvbDevicePyObject__get_pids, METH_VARARGS },
    {"start_recording", DvbDevicePyObject__start_recording, METH_VARARGS },
    {"stop_recording", DvbDevicePyObject__stop_recording, METH_VARARGS },
    {"get_bouquet_list", DvbDevicePyObject__get_bouquet_list, METH_VARARGS },
    { NULL }
};



PyTypeObject DvbDevicePyObject_Type = {
    PyObject_HEAD_INIT(NULL)
    0,                                  /*ob_size*/
    "kaa.record.DvbDevice",             /*tp_name*/
    sizeof(DvbDevicePyObject),          /*tp_basicsize*/
    0,					/*tp_itemsize*/
    (destructor)DvbDevicePyObject__dealloc,  /* tp_dealloc */
    0,					/*tp_print*/
    0,					/* tp_getattr */
    0,					/* tp_setattr*/
    0,					/* tp_compare*/
    0,					/* tp_repr*/
    0,					/* tp_as_number*/
    0,					/* tp_as_sequence*/
    0,					/* tp_as_mapping*/
    0,					/* tp_hash */
    0,					/* tp_call*/
    0,					/* tp_str*/
    0,					/* tp_getattro*/
    0,					/* tp_setattro*/
    0,					/* tp_as_buffer*/
    Py_TPFLAGS_DEFAULT,			/* tp_flags*/
    "DvbDevice Object",			/* tp_doc*/
    0,					/* tp_traverse */
    0,					/* tp_clear */
    0,					/* tp_richcompare */
    0,					/* tp_weaklistoffset */
    0,					/* tp_iter */
    0,					/* tp_iternext */
    DvbDevicePyObject__methods,		/* tp_methods */
    0,					/* tp_members */
    0,					/* tp_getset */
    0,					/* tp_base */
    0,					/* tp_dict */
    0,					/* tp_descr_get */
    0,					/* tp_descr_set */
    0,					/* tp_dictoffset */
    (initproc)DvbDevicePyObject__init,  /* tp_init */
    0,					/* tp_alloc */
    PyType_GenericNew,			/* tp_new */
};


static PyMethodDef module_methods[] = {
    { NULL }
};

extern "C"

void init_dvb() {
  PyObject *m;

  m = Py_InitModule("_dvb", module_methods);
  if (PyType_Ready(&DvbDevicePyObject_Type) < 0)
    return;

  PyModule_AddObject(m, "DvbDevice", (PyObject *)&DvbDevicePyObject_Type);
}
