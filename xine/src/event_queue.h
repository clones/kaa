#ifndef __EVENT_QUEUE_H_
#define __EVENT_QUEUE_H_
#include "config.h"

#include <Python.h>
#include <xine.h>

#define Xine_Event_Queue_PyObject_Check(v) ((v)->ob_type == &Xine_Event_Queue_PyObject_Type)

typedef struct {
    PyObject_HEAD

    xine_event_queue_t *queue;
    PyObject *owner_pyobject;  // Event_Queue Queue object
    int xine_object_owner;
    xine_t *xine;

    PyObject *wrapper;
    PyObject *event_callback;
    void *event_callback_data;
} Xine_Event_Queue_PyObject;

extern PyTypeObject Xine_Event_Queue_PyObject_Type;

PyObject *Xine_Event_Queue_PyObject__new(PyTypeObject *, PyObject *, PyObject *);
Xine_Event_Queue_PyObject *pyxine_new_event_queue_pyobject(PyObject *, xine_event_queue_t *, int);


#endif
