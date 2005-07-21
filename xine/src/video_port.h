#ifndef __VIDEO_PORT_H_
#define __VIDEO_PORT_H_
#include "config.h"

#include <Python.h>
#include <xine.h>
#include <xine/video_out.h>

#define Xine_Video_Port_PyObject_Check(v) ((v)->ob_type == &Xine_Video_Port_PyObject_Type)

typedef struct {
    PyObject_HEAD

    PyObject *owner_pyobject; // Post object or Xine object
    int xine_object_owner;
    xine_t *xine;
    xine_video_port_t *vo;

    PyObject *wrapper;
    PyObject *wire_object; // Wired object (PostOut/Stream source list or PostIn/Port target)

    void (*driver_dealloc_cb)(void *);
    void *driver_dealloc_data;
} Xine_Video_Port_PyObject;

extern PyTypeObject Xine_Video_Port_PyObject_Type;

PyObject *Xine_Video_Port_PyObject__new(PyTypeObject *, PyObject *, PyObject *);
Xine_Video_Port_PyObject *pyxine_new_video_port_pyobject(PyObject *, xine_video_port_t *, int);


#endif
