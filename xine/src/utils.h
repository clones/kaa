#ifndef __UTILS_H_
#define __UTILS_H_
#include <Python.h>
#include <xine.h>

void xine_object_to_pyobject_register(void *ptr, PyObject *o);
void xine_object_to_pyobject_unregister(void *ptr);
PyObject *xine_object_to_pyobject_find(void *ptr);

int pyxine_gc_helper_traverse(PyObject ***list, visitproc visit, void *arg);
int pyxine_gc_helper_clear(PyObject ***list);

#define PyDict_SetItemString_STEAL(dict, key, value) \
 { PyObject *_tm=value; PyDict_SetItemString(dict, key, _tm); Py_DECREF(_tm); }

#define PyList_Append_STEAL(list, value) \
 { PyObject *_tm=value; PyList_Append(list, _tm); Py_DECREF(_tm); }


#endif
