#ifndef __AUDIO_PORT_H_
#define __AUDIO_PORT_H_
#include "config.h"

#include <Python.h>
#include <xine.h>

#define Xine_Audio_Port_PyObject_Check(v) ((v)->ob_type == &Xine_Audio_Port_PyObject_Type)

typedef struct {
    PyObject_HEAD

    Xine_PyObject *xine;
    xine_audio_port_t *ao;
    PyObject *owner;  // Post In, Post Out, Xine, or Stream
    int do_dispose;

    PyObject *wrapper,
             *wire_list;  // List of integers which are pointers to PostOut objects connected to us

} Xine_Audio_Port_PyObject;

extern PyTypeObject Xine_Audio_Port_PyObject_Type;

PyObject *Xine_Audio_Port_PyObject__new(PyTypeObject *, PyObject *, PyObject *);
Xine_Audio_Port_PyObject *pyxine_new_audio_port_pyobject(Xine_PyObject *, void *, xine_audio_port_t *, int);


#endif
