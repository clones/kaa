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

    xine_t *xine;
    xine_stream_t *stream;
    int xine_object_owner;

    PyObject *owner_pyobject,
             *master,  // if configured master/slave 
             *audio_source, // reference to PostOut object for audio
             *video_source, // reference to PostOut object for video
             *wrapper;
    PyObject *vo; //tmp
} Xine_Stream_PyObject;

extern PyTypeObject Xine_Stream_PyObject_Type;

PyObject *Xine_Stream_PyObject__new(PyTypeObject *, PyObject *, PyObject *);
Xine_Stream_PyObject *pyxine_new_stream_pyobject(PyObject *, xine_stream_t *, int);


#endif
