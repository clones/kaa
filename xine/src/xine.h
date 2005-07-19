#ifndef __XINE_H_
#define __XINE_H_
#include "config.h"

#include <Python.h>
#include <xine.h>

extern PyObject *xine_error;

#define Xine_PyObject_Check(v) ((v)->ob_type == &Xine_PyObject_Type)

typedef struct {
    PyObject_HEAD
    xine_t *xine;
    PyObject *dependencies, *wrapper, *log_callback;
} Xine_PyObject;

extern PyTypeObject Xine_PyObject_Type;

void xine_object_to_pyobject_register(void *ptr, PyObject *o);
void xine_object_to_pyobject_unregister(void *ptr);
PyObject *xine_object_to_pyobject_find(void *ptr);


#endif
