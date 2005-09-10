#ifndef __VIDEO_PORT_H_
#define __VIDEO_PORT_H_
#include "config.h"

#include <Python.h>
#include <xine.h>
#include <xine/video_out.h>

#define Xine_Video_Port_PyObject_Check(v) ((v)->ob_type == &Xine_Video_Port_PyObject_Type)

typedef struct {
    PyObject_HEAD

    Xine_PyObject *xine;
    xine_video_port_t *vo;
    void *owner; // PostIn, PostOut, Xine, or Stream
    int do_dispose;

    PyObject *driver, // VODriver or None
             *wrapper,
             *wire_list;  // List of integers which are pointers to PostOut objects connected to us

} Xine_Video_Port_PyObject;

extern PyTypeObject Xine_Video_Port_PyObject_Type;

PyObject *Xine_Video_Port_PyObject__new(PyTypeObject *, PyObject *, PyObject *);
Xine_Video_Port_PyObject *pyxine_new_video_port_pyobject(Xine_PyObject *, void *, xine_video_port_t *, PyObject *, int);


#endif
