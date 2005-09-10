#include <Python.h>
#include "dvb_device.h"
#include "op_generic.h"

int debug_level = 100;

typedef struct {
    PyObject_HEAD
    DvbDevice *device;
} DvbDevicePyObject;



PyObject *DvbDevicePyObject__start_recording(PyObject *self, PyObject* args)
{
  int result;
  char *channel;
  std::string channel_str;
  PyObject *plugin_PyObject;
  OutputPlugin* plugin_pointer;

  if (!PyArg_ParseTuple(args, "sO", &channel, &plugin_PyObject)) {
    PyErr_Format(PyExc_ValueError, "Wrong number of arguments");
    return NULL;
  }

  // create stupid reference
  channel_str = channel;

  // get real plugin object
  plugin_PyObject = PyObject_CallMethod(plugin_PyObject, "_create_plugin", "");
  if (plugin_PyObject == NULL) {
    PyErr_Format(PyExc_ValueError, "Can't create C++ plugin");
    return NULL;
  }

  plugin_pointer = (OutputPlugin*) PyCObject_AsVoidPtr(plugin_PyObject);

  result = ((DvbDevicePyObject *)self)->device->start_recording(channel_str, plugin_pointer);
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

  ((DvbDevicePyObject *)self)->device->stop_recording(id);
  Py_INCREF(Py_None);
  return Py_None;
}

PyObject *DvbDevicePyObject__get_bouquet_list(PyObject *self, PyObject* args)
{
  std::vector<bouquet_t> bouquet_list;
  PyObject *result;

  bouquet_list = ((DvbDevicePyObject *)self)->device->get_bouquet_list();
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
  result = ((DvbDevicePyObject *)self)->device->get_card_type();
  return Py_BuildValue("s", result.c_str());
}

PyObject *DvbDevicePyObject__read_fd_data(PyObject *self, PyObject* args)
{
  ((DvbDevicePyObject *)self)->device->read_fd_data();
  Py_INCREF(Py_None);
  return Py_None;
}

PyObject *DvbDevicePyObject__connect_to_notifier(PyObject *self, PyObject* args)
{
  PyObject *socket_dispatcher;

  if (!PyArg_ParseTuple(args,"O", &socket_dispatcher))
    return NULL;
  ((DvbDevicePyObject *)self)->device->connect_to_notifier(socket_dispatcher);
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


static PyMethodDef DvbDevicePyObject__methods[] = {
    { "start_recording", DvbDevicePyObject__start_recording, METH_VARARGS },
    { "stop_recording", DvbDevicePyObject__stop_recording, METH_VARARGS },
    { "get_bouquet_list", DvbDevicePyObject__get_bouquet_list, METH_VARARGS },
    { "get_card_type", DvbDevicePyObject__get_card_type, METH_VARARGS },
    { "connect_to_notifier", DvbDevicePyObject__connect_to_notifier, METH_VARARGS },
    { "read_fd_data", DvbDevicePyObject__read_fd_data, METH_VARARGS },
    { NULL }
};


PyTypeObject DvbDevicePyObject_Type = {
    PyObject_HEAD_INIT(NULL)
    0,                         /*ob_size*/
    "_dvb.DvbDevice",          /*tp_name*/
    sizeof(DvbDevicePyObject),    /*tp_basicsize*/
    0,                         /*tp_itemsize*/
    (destructor)DvbDevicePyObject__dealloc, /* tp_dealloc */
    0,                         /*tp_print*/
    0,                         /* tp_getattr */
    0,                         /* tp_setattr*/
    0,                         /* tp_compare*/
    0,                         /* tp_repr*/
    0,                         /* tp_as_number*/
    0,                         /* tp_as_sequence*/
    0,                         /* tp_as_mapping*/
    0,                         /* tp_hash */
    0,                         /* tp_call*/
    0,                         /* tp_str*/
    0,                         /* tp_getattro*/
    0,                         /* tp_setattro*/
    0,                         /* tp_as_buffer*/
    Py_TPFLAGS_DEFAULT,        /* tp_flags*/
    "Record Tuner Object",     /* tp_doc*/
    0,		               /* tp_traverse */
    0,		               /* tp_clear */
    0,		               /* tp_richcompare */
    0,		               /* tp_weaklistoffset */
    0,		               /* tp_iter */
    0,		               /* tp_iternext */
    DvbDevicePyObject__methods,   /* tp_methods */
    0,                         /* tp_members */
    0,                         /* tp_getset */
    0,                         /* tp_base */
    0,                         /* tp_dict */
    0,                         /* tp_descr_get */
    0,                         /* tp_descr_set */
    0,                         /* tp_dictoffset */
    (initproc)DvbDevicePyObject__init,      /* tp_init */
    0,                         /* tp_alloc */
    PyType_GenericNew,         /* tp_new */
};


PyMethodDef dvb_methods[] = {
    { NULL }
};


extern "C"
void init_dvb() {
  PyObject *m;

  PyObject *nfModule;
  PyObject *nfName;

  PyObject *nfDict, *nfFunc, *nfArgs;
  PyObject *nfInstance;

  m = Py_InitModule("_dvb", dvb_methods);
  if (PyType_Ready(&DvbDevicePyObject_Type) < 0)
    return;

  PyModule_AddObject(m, "DvbDevice", (PyObject *)&DvbDevicePyObject_Type);
}
