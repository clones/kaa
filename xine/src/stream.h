#ifndef __STREAM_H_
#define __STREAM_H_
#include "config.h"

#include <Python.h>
#include <xine.h>

#include "video_port.h"
#include "audio_port.h"

#define Xine_Stream_PyObject_Check(v) ((v)->ob_type == &Xine_Stream_PyObject_Type)

typedef struct {
    PyObject_HEAD

    PyObject *xine_pyobject;
    Xine_Video_Port_PyObject *vo_pyobject;
    Xine_Audio_Port_PyObject *ao_pyobject;
    xine_t *xine;
    xine_stream_t *stream;
    int xine_object_owner;
    PyObject *master;

    PyObject *wrapper;
} Xine_Stream_PyObject;

extern PyTypeObject Xine_Stream_PyObject_Type;

PyObject *Xine_Stream_PyObject__new(PyTypeObject *, PyObject *, PyObject *);
Xine_Stream_PyObject *pyxine_new_stream_pyobject(Xine_PyObject *, xine_stream_t *, 
    Xine_Audio_Port_PyObject *ao, Xine_Video_Port_PyObject *vo, int);


#endif
