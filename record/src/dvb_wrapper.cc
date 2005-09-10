#include <Python.h>
#include "dvb_device.h"
#include "filter.h"

int debug_level = 100;

typedef struct {
    PyObject_HEAD
    DvbDevice *device;
} DvbDevicePyObject;

PyObject *PyFromIntVector(std::vector< int >& v) 
{
    int i;
    PyObject *list = PyList_New(v.size());
    for (i = 0; i < v.size(); i++)
	PyList_Insert(list, i, PyInt_FromLong(v[i]));
    return list;
}

PyObject *DvbDevicePyObject__get_pids(PyObject *self, PyObject* args)
{
    char *channel;
    std::vector< int > video_pids, audio_pids, ac3_pids, teletext_pids, subtitle_pids;
    
    if (!PyArg_ParseTuple(args, "sO", &channel))
	return NULL;
    self->device->get_pids(channel, video_pids, audio_pids, ac3_pids, 
			   teletext_pids, subtitle_pids );
    PyObject *list = PyList_New(5);
    PyList_Insert(list, 0, PyFromIntVector(video_pids));
    PyList_Insert(list, 0, PyFromIntVector(audio_pids));
    PyList_Insert(list, 0, PyFromIntVector(ac3_pids));
    PyList_Insert(list, 0, PyFromIntVector(teletext_pids));
    PyList_Insert(list, 0, PyFromIntVector(subtitle_pids));
    return list;
}


PyObject *DvbDevicePyObject__start_recording(PyObject *self, PyObject* args)
{
    int result;
    char *channel;
    std::string channel_str;
    PyObject *plugin_PyObject;
    FilterData* plugin_pointer;
    
    if (!PyArg_ParseTuple(args, "sO", &channel, &plugin_PyObject))
	return NULL;
    
    // create stupid reference
    channel_str = channel;
    
    // get real plugin object
    plugin_PyObject = PyObject_GetAttrString(plugin_PyObject, "_get_chain");
    if (plugin_PyObject == NULL) {
	PyErr_Format(PyExc_ValueError, "can't create filter plugin");
	return NULL;
    }
    
    plugin_pointer = (FilterData*) PyCObject_AsVoidPtr(plugin_PyObject);
    
    result = self->device->start_recording(channel_str, *plugin_pointer);
    Py_DECREF(plugin_PyObject);
    return Py_BuildValue("i", result);
}


PyObject *DvbDevicePyObject__stop_recording(PyObject *self, PyObject* args)
{
  int id;

  if (!PyArg_ParseTuple(args, "i", &id)) {
    PyErr_Format(PyExc_ValueError, "Wrong number of arguments");
    return NULL;
  }

  self->device->stop_recording(id);
  Py_INCREF(Py_None);
  return Py_None;
}

PyObject *DvbDevicePyObject__get_bouquet_list(PyObject *self, PyObject* args)
{
  std::vector<bouquet_t> bouquet_list;
  PyObject *result;

  bouquet_list = self->device->get_bouquet_list();
  result = PyList_New(bouquet_list.size());
  for (int i=0; i<bouquet_list.size(); i++) {
    std::vector< bouquet_channel_t > &channels = bouquet_list[i].channels;
    PyObject *l = PyList_New(channels.size());
    PyList_SetItem(result, i, l);
    for (int j=0; j<channels.size(); j++) {
      PyObject *c = PyString_FromString(channels[j].name.c_str());
      PyList_SetItem(l, j, c);
    }
  }
  return result;
}

PyObject *DvbDevicePyObject__get_card_type(PyObject *self, PyObject* args)
{
  std::string result;
  result = self->device->get_card_type();
  return Py_BuildValue("s", result.c_str());
}

PyObject *DvbDevicePyObject__read_fd_data(PyObject *self, PyObject* args)
{
  self->device->read_fd_data();
  Py_INCREF(Py_None);
  return Py_None;
}

PyObject *DvbDevicePyObject__connect_to_notifier(PyObject *self, PyObject* args)
{
  PyObject *socket_dispatcher;

  if (!PyArg_ParseTuple(args,"O", &socket_dispatcher))
    return NULL;
  self->device->connect_to_notifier(socket_dispatcher);
  Py_INCREF(Py_None);
  return Py_None;
}

void DvbDevicePyObject__dealloc(DvbDevicePyObject *self)
{
    delete self->device;
    PyMem_DEL(self);
}

static int DvbDevicePyObject__init(DvbDevicePyObject *self, PyObject *args)
{
  char *adapter;
  char *channels;
  int prio;

  if (!PyArg_ParseTuple(args,"ssi", &adapter, &channels, &prio))
    return -1;

  self->device = new DvbDevice(adapter, channels, prio);
  return 0;
}



static PyMethodDef module_methods[] = {
    { NULL }
};

extern "C"

void init_dvb() {
  PyObject *m;

  PyObject *nfModule;
  PyObject *nfName;

  PyObject *nfDict, *nfFunc, *nfArgs;
  PyObject *nfInstance;

  m = Py_InitModule("_dvb", module_methods);
  if (PyType_Ready(&DvbDevicePyObject_Type) < 0)
    return;

  PyModule_AddObject(m, "DvbDevice", (PyObject *)&DvbDevicePyObject_Type);
}
