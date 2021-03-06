/* File: filter.cc
 *
 * Author: S�nke Schwardt <schwardt@users.sourceforge.net>
 *
 * $Id$
 *
 * Copyright (C) 2004 S�nke Schwardt <schwardt@users.sourceforge.net>
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

#include <set>

#include "misc.h"
#include "fp_generic.h"
#include "fdsplitter.h"

using namespace std;


FDSplitter::FDSplitter( int fd ) :
  idcounter(0), inputtype(INPUT_RAW), fd(fd)
{
  ;
}


FDSplitter::~FDSplitter() {
  printD( LOG_DEBUG, "destroying FDSplitter\n");

  // iterate through all registered filters and destroy corresponding output plugin

  std::map<int, FilterChain>::iterator iter;
  // iterate through all FilterChain
  for( iter = id2filter.begin() ; iter != id2filter.end() ; ++iter) {
    // iterate through filterlist
    while(iter->second.filterlist.size() > 0) {
      delete iter->second.filterlist[0];
      iter->second.filterlist.erase( iter->second.filterlist.begin() );
    }
  }
}


void FDSplitter::set_input_type( InputType inputtype ) {
  if ((INPUT_RAW <= inputtype) &&
      (inputtype <= INPUT_LAST)) {
    this->inputtype = inputtype;
  }
  char *s;
  switch(inputtype) {
  case INPUT_RAW: s="INPUT_RAW"; break;
  case INPUT_TS:  s="INPUT_TS"; break;
  default: s="UNKNOWN";
  } 
  printD( LOG_DEBUG, "set input type to %s (%d)\n", s, (int)inputtype );
}


int FDSplitter::add_filter_chain( FilterChain &fdata ) {

  int id = idcounter;
  // register new filter
  id2filter[ id ] = fdata;
  // add output plugin to requested pid
  for(int i=fdata.pids.size()-1; i >= 0 ; --i) {
    pid2id[ fdata.pids[i] ].push_back( id );
    printD( LOG_DEBUG_FILTER, "Added output filter chain %d to pid %d\n", id, fdata.pids[i] );
  }
  // jump to next id :-)
  ++idcounter;

  return id;
}


bool FDSplitter::remove_filter_chain( int id ) {
  // check if filter id does exist
  if ( id2filter.find(id) != id2filter.end() ) {

    // interate over every pid for this filter id
    for(unsigned int i = 0; i < id2filter[id].pids.size(); ++i) {
      int pid = id2filter[id].pids[i];
      // iterate through all output plugins that are registered to "pid"
      int size = pid2id[ pid ].size();
      for( int t = size-1; t >= 0; --t ) {
	// if output plugin matches with output plugin of requested filter id
	if ( pid2id[ pid ][t] == id ) {
	  // then remove it
	  pid2id[ pid ].erase( pid2id[ pid ].begin() + t );
	  printD( LOG_DEBUG_FILTER, "Removed filter chain %d from pid %d\n", id, pid );
	}
      }
    }

    // free filter chain
    while(id2filter[id].filterlist.size() > 0) {
      delete id2filter[id].filterlist[0];
      id2filter[id].filterlist.erase( id2filter[id].filterlist.begin() );
    }

    // remove filter id from id2filter
    id2filter.erase( id2filter.find(id) );
    printD( LOG_DEBUG_FILTER, "Removed filter chain with id %d\n", id );

    return true;
  }

  return false;
}


void FDSplitter::add_data( std::string &data ) {
  // append new data to buffer
  buffer.append( data );

  process_data();
}


void FDSplitter::read_fd_data() {
  // read data von fd_dvr and pass it to filter via filter.process_data()
  static char buf[ FDSplitter::BUFFERSIZE ];

  int len = read( fd, buf, FDSplitter::BUFFERSIZE );
  if ( len < 0 ) {
    printD( LOG_WARN,
	    "WARNING: read failed: errno=%d  err=%s\n",
	    errno, strerror(errno) );
  }
  if ( len > 0 ) {
    // TODO FIXME some kind of ugly
    buffer.append( buf, len );
  }

  process_data();
}


void FDSplitter::process_data() {

  switch(inputtype) {
  case INPUT_RAW:
    process_new_data_RAW();
    break;
  case INPUT_TS:
    process_new_data_TS();
    break;
  }

  process_filter_chain();
}


void FDSplitter::process_new_data_TS() {

  unsigned int i;

  // should be at least two transport stream frames
  if (buffer.length() < 2*188) {
    printD( LOG_WARN, "not enough data\n");
    return;
  }

  // check if they are really transport stream frames
  for ( i = 0; i < 188 ; i++){
    if (( buffer[i] == 0x47 ) &&
	( buffer[i+188] == 0x47 ))break;
  }
  if ( i == 188){
    printD( LOG_WARN, "not a transport stream\n");
    return;
  } else if (i) {
    printD( LOG_WARN, "dropping %d bytes to get TS in sync\n", i);
    // if unequal 0 then cutoff bogus
    buffer.erase(0,i);
  }

  i = 0;
  int buflen = buffer.size();

  typedef set< int, greater<int> > ID_Set;
  ID_Set id_set;

  // iterate through all complete frames
  while( buflen - i >= 188 ) {

    // check frame
    if (buffer[i] != 0x47) {

      // frame invalid
      printD( LOG_VERBOSE, "invalid ts frame 0x%02x\n", buffer[i] );

    } else {

      // frame ok
      bool ts_error = ((int)(buffer[i+1] & 0x80) >> 7);
      //       bool pusi     = ((int)(buffer[i+1] & 0x40) >> 6);
      //       bool ts_prio  = ((int)(buffer[i+1] & 0x20) >> 5);
      int  pid      = ((((int)buffer[i+1] & 0x1F) << 8) | ((int)buffer[i+2] & 0xFF));
      int  ts_sc    = ((int)(buffer[i+3] & 0xC0) >> 6);
      //       int  afc      = ((int)(buffer[i+3] & 0x30) >> 4);
      //       int  cc       = ((int)(buffer[i+3] & 0x0F));
      // printD( LOG_DEBUG_FILTER,
      //         "offset=%05d  ts_error=%d  pusi=%d  ts_prio=%d  pid=%d  ts_sc=%d  afc=%d  cc=%d\n",
      // 	 i, ts_error, pusi, ts_prio, pid, ts_sc, afc, cc );

      // TODO implement counter to reduce output
      if (ts_error) {
	printD( LOG_DEBUG_FILTER, "ts frame is damaged!\n");
      }
      if (ts_sc) {
	printD( LOG_VERBOSE, "ts frame is scrambled!\n");
      }

      // iterate over all registered filter plugins for this pid
      int size = pid2id[ pid ].size();
      for( int plugi = 0; plugi < size; ++plugi ) {
	// pass ts frame to filter plugin
	id2filter[ pid2id[ pid ][plugi] ].filterlist[0]->add_data( buffer.substr(i,188) );
	// remember output plugin to call flush() only on those filter plugins which received data
	id_set.insert( pid2id[ pid ][plugi] );
      }
    }
    // jump to next ts frame
    i += 188;
  }

  buffer.erase(0,i);

  // call flush on all filter plugins that received new data
  for( ID_Set::iterator iter = id_set.begin(); iter != id_set.end() ; ++iter ) {
    id2filter[ (*iter) ].filterlist[0]->process_data();
  }
}


void FDSplitter::process_new_data_RAW() {

  std::map<int, FilterChain>::iterator iter;
  // iterate over all registered filter chains
  for( iter=id2filter.begin(); iter != id2filter.end(); ++iter) {
    // add data to first filter plugin in chain
    iter->second.filterlist[0]->add_data( buffer );
    // process data
    iter->second.filterlist[0]->process_data();
  }

  buffer.erase();
}


void FDSplitter::process_filter_chain() {
  std::map<int, FilterChain>::iterator iterFD;
  // iterate over all registered filter chains
  for( iterFD=id2filter.begin(); iterFD != id2filter.end(); ++iterFD) {

    for(unsigned int i=1; i < iterFD->second.filterlist.size(); ++i) {
      // get data from previous filter and add it to current filter
      iterFD->second.filterlist[i]->add_data( iterFD->second.filterlist[i-1]->get_data() );
      // process data
      iterFD->second.filterlist[i]->process_data();
    }
  }
}


/* ********************* PYTHON WRAPPER CODE ************************ */


int debug_level = 65535;

#define FDSPLITTER ((FDSplitterPyObject *)self)->fdsplitter

typedef struct {
    PyObject_HEAD
    FDSplitter *fdsplitter;
} FDSplitterPyObject;


PyObject *PyFromIntVector(std::vector< int >& v)
{
    PyObject *list = PyList_New(0);
    for (unsigned int i = 0; i < v.size(); i++)
      PyList_Append(list, PyInt_FromLong(v[i]));
    return list;
}

PyObject *FDSplitterPyObject__set_input_type(PyObject *self, PyObject* args)
{
  int inputtype;

  if (!PyArg_ParseTuple(args,"i", &inputtype))
    return NULL;

  FDSPLITTER->set_input_type( (FDSplitter::InputType)inputtype );

  Py_INCREF(Py_None);
  return Py_None;
}


PyObject *FDSplitterPyObject__add_filter_chain(PyObject *self, PyObject* args)
{
  int result;
  PyObject *plugin_PyObject;
  FilterChain* plugin_pointer;

  if (!PyArg_ParseTuple(args, "O", &plugin_PyObject))
    return NULL;

  plugin_pointer = (FilterChain*) PyCObject_AsVoidPtr(plugin_PyObject);

  result = FDSPLITTER->add_filter_chain( *plugin_pointer );

  return Py_BuildValue("i", result);
}


PyObject *FDSplitterPyObject__remove_filter_chain(PyObject *self, PyObject* args)
{
  int id;

  if (!PyArg_ParseTuple(args, "i", &id))
    return NULL;

  FDSPLITTER->remove_filter_chain(id);
  Py_INCREF(Py_None);
  return Py_None;
}


// FIXME TODO
// void FDSplitter::add_data( std::string &data ) {


PyObject *FDSplitterPyObject__read_fd_data(PyObject *self, PyObject* args)
{
  FDSPLITTER->read_fd_data();
  Py_INCREF(Py_None);
  return Py_None;
}


void FDSplitterPyObject__dealloc(FDSplitterPyObject *self)
{
    delete self->fdsplitter;
    PyMem_DEL(self);
}


static int FDSplitterPyObject__init(FDSplitterPyObject *self, PyObject *args)
{
  int fd;

  if (!PyArg_ParseTuple(args,"i", &fd))
    return -1;

  self->fdsplitter = new FDSplitter( fd );
  return 0;
}


static PyMethodDef FDSplitterPyObject__methods[] = {
    {"set_input_type", FDSplitterPyObject__set_input_type, METH_VARARGS },
    {"add_filter_chain", FDSplitterPyObject__add_filter_chain, METH_VARARGS },
    {"remove_filter_chain", FDSplitterPyObject__remove_filter_chain, METH_VARARGS },
    {"read_fd_data", FDSplitterPyObject__read_fd_data, METH_VARARGS },
    { NULL }
};



PyTypeObject FDSplitterPyObject_Type = {
    PyObject_HEAD_INIT(NULL)
    0,                                  /*ob_size*/
    "kaa.record.FDSplitter",            /*tp_name*/
    sizeof(FDSplitterPyObject),         /*tp_basicsize*/
    0,					/*tp_itemsize*/
    (destructor)FDSplitterPyObject__dealloc,  /* tp_dealloc */
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
    "FDSplitter Object",		/* tp_doc*/
    0,					/* tp_traverse */
    0,					/* tp_clear */
    0,					/* tp_richcompare */
    0,					/* tp_weaklistoffset */
    0,					/* tp_iter */
    0,					/* tp_iternext */
    FDSplitterPyObject__methods,	/* tp_methods */
    0,					/* tp_members */
    0,					/* tp_getset */
    0,					/* tp_base */
    0,					/* tp_dict */
    0,					/* tp_descr_get */
    0,					/* tp_descr_set */
    0,					/* tp_dictoffset */
    (initproc)FDSplitterPyObject__init,  /* tp_init */
    0,					/* tp_alloc */
    PyType_GenericNew,			/* tp_new */
};


static PyMethodDef module_methods[] = {
    { NULL }
};

extern "C"

void init_fdsplitter() {
  PyObject *m;

  m = Py_InitModule("_fdsplitter", module_methods);
  if (PyType_Ready(&FDSplitterPyObject_Type) < 0)
    return;

  PyModule_AddObject(m, "FDSplitter", (PyObject *)&FDSplitterPyObject_Type);
}
