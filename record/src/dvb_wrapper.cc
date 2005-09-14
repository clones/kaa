#include <Python.h>
#include "dvb_device.h"
#include "fdsplitter.h"

int debug_level = 65535;

#define DEVICE ((DvbDevicePyObject *)self)->device

typedef struct {
    PyObject_HEAD
    DvbDevice *device;
} DvbDevicePyObject;


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

    // create stupid reference
    channel_str = channel;

    plugin_pointer = (FilterChain*) PyCObject_AsVoidPtr(plugin_PyObject);

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


PyObject *DvbDevicePyObject__get_card_type(PyObject *self, PyObject* args)
{
  std::string result;
  result = DEVICE->get_card_type();
  return Py_BuildValue("s", result.c_str());
}


PyObject *DvbDevicePyObject__get_fd(PyObject *self, PyObject* args)
{
  return Py_BuildValue("i", DEVICE->get_fd());
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

  if (!PyArg_ParseTuple(args,"ss", &adapter, &channels))
    return -1;

  self->device = new DvbDevice(adapter, channels);
  return 0;
}


static PyMethodDef DvbDevicePyObject__methods[] = {
    {"get_pids", DvbDevicePyObject__get_pids, METH_VARARGS },
    {"start_recording", DvbDevicePyObject__start_recording, METH_VARARGS },
    {"stop_recording", DvbDevicePyObject__stop_recording, METH_VARARGS },
    {"get_bouquet_list", DvbDevicePyObject__get_bouquet_list, METH_VARARGS },
    {"get_card_type", DvbDevicePyObject__get_card_type, METH_VARARGS },
    {"get_fd", DvbDevicePyObject__get_fd, METH_VARARGS },
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

//   PyObject *nfModule;
//   PyObject *nfName;

//   PyObject *nfDict, *nfFunc, *nfArgs;
//   PyObject *nfInstance;

  m = Py_InitModule("_dvb", module_methods);
  if (PyType_Ready(&DvbDevicePyObject_Type) < 0)
    return;

  PyModule_AddObject(m, "DvbDevice", (PyObject *)&DvbDevicePyObject_Type);
}
