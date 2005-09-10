#include <Python.h>
#include "filter.h"
#include "fp_remux.h"
#include "fp_filewriter.h"

int debug_level = 100;

typedef struct {
    PyObject_HEAD
    FilterData *chain;
} ChainPyObject;


static int ChainPyObject__init(ChainPyObject *self, PyObject *args)
{
    self->chain = new FilterData();
    return 0;
}

void ChainPyObject__dealloc(ChainPyObject *self)
{
    delete self->chain;
    PyMem_DEL(self);
}

PyObject *ChainPyObject__append(PyObject *self, PyObject* args)
{
    PyObject *filter;
    
    if (!PyArg_ParseTuple(args,"O", &filter))
	return NULL;

    PyObject *plugin_PyObject = PyObject_CallMethod(filter, "_create_filter", "");
    if (!plugin_PyObject)
	return NULL;
    if (!PyCObject_Check(plugin_PyObject)) {
        PyErr_Format(PyExc_AttributeError, "expected CObject");
	Py_DECREF(plugin_PyObject);
	return NULL;
    }
    self->chain->filterlist.push_back((FilterPlugin*) PyCObject_AsVoidPtr(plugin_PyObject));
    
    Py_DECREF(plugin_PyObject);
    Py_INCREF(Py_None);
    return Py_None;
}


PyObject *ChainPyObject__get_chain(PyObject *self, PyObject* args)
{
    return PyCObject_FromVoidPtr((void*) self->chain, NULL);
}


PyObject *ChainPyObject__add_pid(PyObject *self, PyObject* args)
{
    int pid;
    
    if (!PyArg_ParseTuple(args,"i", &pid))
	return NULL;
    self->chain->pids.push_back(pid);
}


PyObject *create_remux(PyObject *self, PyObject* args)
{
    int vpid;
    int apid;

    printf("create remux\n");

    // TODO: support other pids
    if (!PyArg_ParseTuple(args,"ii", &vpid, &apid))
	return NULL;

    std::vector<int> pids_a, pids_d, pids_s;
    pids_a.push_back(apid);
    
    FPRemux *filter = new FPRemux();
    filter->set_pids(vpid, pids_a, pids_d, pids_s);
    return PyCObject_FromVoidPtr((void*) filter, NULL);
}

PyObject *create_filewriter(PyObject *self, PyObject* args)
{
    char *fname;
    int chunksize;
    
    printf("create filewriter\n");
    
    if (!PyArg_ParseTuple(args,"si", &fname, &chunksize))
	return NULL;

    FPFilewriter *filter = new FPFilewriter(fname, chunksize);
    return PyCObject_FromVoidPtr((void*) filter, NULL);
}

PyMethodDef module_methods[] = {
    { "create_remux", create_remux, METH_VARARGS }, 
    { "create_filewriter", create_filewriter, METH_VARARGS }, 
    { NULL }
};

extern "C"
void init_filter() {
  PyObject *m = Py_InitModule("_filter", module_methods);

  if (PyType_Ready(&ChainPyObject_Type) >= 0)
      PyModule_AddObject(m, "Chain", (PyObject *)&ChainPyObject_Type);
}
