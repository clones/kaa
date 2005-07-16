#ifndef __AUDIO_PORT_H_
#define __AUDIO_PORT_H_
#include "config.h"

#include <Python.h>
#include <xine.h>

#define Xine_Audio_Port_PyObject_Check(v) ((v)->ob_type == &Xine_Audio_Port_PyObject_Type)

typedef struct {
    PyObject_HEAD


    xine_audio_port_t *ao;
    int owns_ref;
    PyObject *xine_pyobject;
    xine_t *xine;
} Xine_Audio_Port_PyObject;

extern PyTypeObject Xine_Audio_Port_PyObject_Type;

PyObject *Xine_Audio_Port_PyObject__new(PyTypeObject *, PyObject *, PyObject *);


#endif
