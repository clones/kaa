#ifndef __AUDIO_PORT_H_
#define __AUDIO_PORT_H_
#include "config.h"

#include <Python.h>
#include <xine.h>

#define Xine_Audio_Port_PyObject_Check(v) ((v)->ob_type == &Xine_Audio_Port_PyObject_Type)

typedef struct {
    PyObject_HEAD

    xine_audio_port_t *ao;
    PyObject *owner_pyobject;  // Post object or Xine object
    int xine_object_owner;
    xine_t *xine;

    PyObject *wrapper;
    PyObject *wire_object; // Wired object (PostOut/Stream or PostIn/Port)
    PyObject *up, *down;

} Xine_Audio_Port_PyObject;

extern PyTypeObject Xine_Audio_Port_PyObject_Type;

PyObject *Xine_Audio_Port_PyObject__new(PyTypeObject *, PyObject *, PyObject *);
Xine_Audio_Port_PyObject *pyxine_new_audio_port_pyobject(PyObject *, xine_audio_port_t *, int);


#endif
