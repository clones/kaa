#include <Python.h>
#include "op_filewriter.h"

int debug_level = 100;

PyObject *create_OutputPluginFilewriter(PyObject *self, PyObject* args)
{
  char *filename;
  int chunksize;
  int int_type;
  OutputPluginFilewriter::FileType file_type;
  OutputPlugin *plugin;
  
  if (!PyArg_ParseTuple(args, "sii", &filename, &chunksize, &int_type)) {
    PyErr_Format(PyExc_ValueError, "");
    return NULL;
  }

  switch (int_type) {
  case 0:
    file_type = OutputPluginFilewriter::FT_RAW;
    break;
  case 1:
    file_type = OutputPluginFilewriter::FT_MPEG;
    break;
  default:
    PyErr_Format(PyExc_ValueError, "Invalid file type");
    return NULL;
  };
  
  plugin = (OutputPlugin*) new OutputPluginFilewriter(filename, 0, file_type);
  return PyCObject_FromVoidPtr(plugin, NULL);
}

PyMethodDef op_methods[] = {
    { "Filewriter", create_OutputPluginFilewriter, METH_VARARGS },
    { NULL }
};

extern "C"
void init_op() {
  Py_InitModule("_op", op_methods);
}
