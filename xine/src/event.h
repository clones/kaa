#ifndef __EVENT_H_
#define __EVENT_H_
#include "config.h"

#include <Python.h>
#include <xine.h>

#define Xine_Event_PyObject_Check(v) ((v)->ob_type == &Xine_Event_PyObject_Type)

typedef struct {
    PyObject_HEAD

    xine_event_t *event;
    PyObject *owner_pyobject;  // Event Queue object
    int xine_object_owner;
    xine_t *xine;

    PyObject *wrapper;

} Xine_Event_PyObject;

extern PyTypeObject Xine_Event_PyObject_Type;

PyObject *Xine_Event_PyObject__new(PyTypeObject *, PyObject *, PyObject *);
Xine_Event_PyObject *pyxine_new_event_pyobject(PyObject *, xine_event_t *, int);


#endif
