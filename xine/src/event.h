#ifndef __EVENT_H_
#define __EVENT_H_
#include "config.h"

#include <Python.h>
#include <xine.h>

#define Xine_Event_PyObject_Check(v) ((v)->ob_type == &Xine_Event_PyObject_Type)

typedef struct {
    PyObject_HEAD

    Xine_PyObject *xine;
    xine_event_t *event;
    void *owner;  // Event Queue object
    int do_dispose;

    PyObject *wrapper,
             *type,
             *data;
} Xine_Event_PyObject;

extern PyTypeObject Xine_Event_PyObject_Type;

PyObject *Xine_Event_PyObject__new(PyTypeObject *, PyObject *, PyObject *);
Xine_Event_PyObject *pyxine_new_event_pyobject(Xine_PyObject *, void *, xine_event_t *, int);


#endif
