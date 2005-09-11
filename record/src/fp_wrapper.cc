#include <Python.h>
#include "filter.h"
#include "fp_remux.h"
#include "fp_filewriter.h"
#include "fp_udpsend.h"

int debug_level = 100;

typedef struct {
    PyObject_HEAD
    FilterData *chain;
} ChainPyObject;

#define CHAIN ((ChainPyObject *)self)->chain

static int ChainPyObject__init(ChainPyObject *self, PyObject *args)
{
    self->chain = new FilterData();
    return 0;
}

void ChainPyObject__dealloc(ChainPyObject *self)
{
  // FIXME: why does this crash?
  // delete self->chain;
  PyMem_DEL(self);
}

PyObject *ChainPyObject__append(PyObject *self, PyObject* args)
{
    PyObject *filter;
    
    if (!PyArg_ParseTuple(args,"O", &filter))
	return NULL;

    PyObject *plugin_PyObject = PyObject_CallMethod(filter, "_create", "");
    if (!plugin_PyObject)
	return NULL;

    if (!PyCObject_Check(plugin_PyObject)) {
        PyErr_Format(PyExc_AttributeError, "expected CObject");
	Py_DECREF(plugin_PyObject);
	return NULL;
    }
    CHAIN->filterlist.push_back((FilterPlugin*) PyCObject_AsVoidPtr(plugin_PyObject));
    
    Py_DECREF(plugin_PyObject);
    Py_INCREF(Py_None);
    return Py_None;
}


PyObject *ChainPyObject__get_chain(PyObject *self, PyObject* args)
{
    return PyCObject_FromVoidPtr((void*) CHAIN, NULL);
}


PyObject *ChainPyObject__add_pid(PyObject *self, PyObject* args)
{
    int pid;
    
    if (!PyArg_ParseTuple(args,"i", &pid))
	return NULL;
    CHAIN->pids.push_back(pid);
    Py_INCREF(Py_None);
    return Py_None;
}

static PyMethodDef ChainPyObject__methods[] = {
    {"append", ChainPyObject__append, METH_VARARGS },
    {"get_chain", ChainPyObject__get_chain, METH_VARARGS },
    {"add_pid", ChainPyObject__add_pid, METH_VARARGS },
    { NULL }
};



PyTypeObject ChainPyObject_Type = {
    PyObject_HEAD_INIT(NULL)
    0,                                  /* ob_size*/
    "kaa.record.Chain",                 /* tp_name*/
    sizeof(ChainPyObject),              /* tp_basicsize*/
    0,					/* tp_itemsize*/
    (destructor)ChainPyObject__dealloc, /* tp_dealloc */
    0,					/* tp_print*/
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
    "Chain Object",			/* tp_doc*/
    0,					/* tp_traverse */
    0,					/* tp_clear */
    0,					/* tp_richcompare */
    0,					/* tp_weaklistoffset */
    0,					/* tp_iter */
    0,					/* tp_iternext */
    ChainPyObject__methods,		/* tp_methods */
    0,					/* tp_members */
    0,					/* tp_getset */
    0,					/* tp_base */
    0,					/* tp_dict */
    0,					/* tp_descr_get */
    0,					/* tp_descr_set */
    0,					/* tp_dictoffset */
    (initproc)ChainPyObject__init,      /* tp_init */
    0,					/* tp_alloc */
    PyType_GenericNew,			/* tp_new */
};


PyMethodDef module_methods[] = {
    { "Remux", PyFilter_Remux, METH_VARARGS }, 
    { "Filewriter", PyFilter_Filewriter, METH_VARARGS }, 
    { "UDPSend", PyFilter_UDPSend, METH_VARARGS }, 
    { NULL }
};

extern "C"
void init_filter() {
  PyObject *m = Py_InitModule("_filter", module_methods);

  if (PyType_Ready(&ChainPyObject_Type) >= 0)
      PyModule_AddObject(m, "Chain", (PyObject *)&ChainPyObject_Type);
}
