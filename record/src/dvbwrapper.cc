#include <Python.h>
#include "dvbdevice.h"
#include "op_filewriter.h"

int debug_level = 100;

typedef struct {
    PyObject_HEAD
    DvbDevice *device;
} DvbDevicePyObject;


PyObject *DvbDevicePyObject__start_recording(PyObject *self, PyObject* args)
{
  int result;
  char *chan_name;
  char *filename;
  std::string chan_name_str;
  OutputPluginFilewriter *plugin = NULL;
  
  if (!PyArg_ParseTuple(args, "ss", &chan_name, &filename)) {
    PyErr_Format(PyExc_ValueError, "");
    return NULL;
  }

  // create stupid reference
  chan_name_str = chan_name;
  
  plugin = new OutputPluginFilewriter(filename, 0, OutputPluginFilewriter::FT_MPEG);
  result = ((DvbDevicePyObject *)self)->device->start_recording(chan_name_str, plugin);
  return Py_BuildValue("i", result);
}

PyObject *DvbDevicePyObject__stop_recording(PyObject *self, PyObject* args)
{
  int id;
  
  if (!PyArg_ParseTuple(args, "i", &id)) {
    PyErr_Format(PyExc_ValueError, "");
    return NULL;
  }
  
  ((DvbDevicePyObject *)self)->device->stop_recording(id);
  Py_INCREF(Py_None);
  return Py_None;
}

PyObject *DvbDevicePyObject__get_bouquet_list(PyObject *self, PyObject* args)
{
  std::vector<bouquet_t> result;
  result = ((DvbDevicePyObject *)self)->device->get_bouquet_list();
  // FIXME: return the result as python list
  Py_INCREF(Py_None);
  return Py_None;
}

PyObject *DvbDevicePyObject__get_card_type(PyObject *self, PyObject* args)
{
  std::string result;
  result = ((DvbDevicePyObject *)self)->device->get_card_type();
  return Py_BuildValue("s", result.c_str());
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
    { NULL }
};


PyTypeObject DvbDevicePyObject_Type = {
    PyObject_HEAD_INIT(NULL)
    0,                         /*ob_size*/
    "_Record.Tuner",           /*tp_name*/
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
void initdvb() {
  PyObject *m;
  
  PyObject *nfModule;
  PyObject *nfName;
  
  PyObject *nfDict, *nfFunc, *nfArgs;
  PyObject *nfInstance;

  m = Py_InitModule("dvb", dvb_methods);
  if (PyType_Ready(&DvbDevicePyObject_Type) < 0)
    return;

//   nfName=PyString_FromString("foo");
//   nfModule = PyImport_Import(nfName);
//   Py_DECREF(nfName);

//   nfDict = PyModule_GetDict(nfModule);
//   nfFunc = PyDict_GetItemString(nfDict, "x");
//   Py_DECREF(nfDict);

//   nfDict = PyDict_New();
//   nfArgs = PyTuple_New(1);

//   PyTuple_SetItem(nfArgs, 0, PyInt_FromLong(0));
//   nfInstance = PyInstance_New(nfFunc, nfArgs, nfDict);
//   Py_DECREF(nfDict);
//   Py_DECREF(nfArgs);
  
//   nfName=PyString_FromString("y");
//   PyMethod_New(nfName, nfInstance, nfFunc);
  
  PyModule_AddObject(m, "DvbDevice", (PyObject *)&DvbDevicePyObject_Type);
}
