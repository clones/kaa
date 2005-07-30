#ifndef __VO_DRIVER_H_
#define __VO_DRIVER_H_
#include "config.h"

#include <Python.h>
#include <xine.h>
#include <xine/video_out.h>

#define Xine_VO_Driver_PyObject_Check(v) ((v)->ob_type == &Xine_VO_Driver_PyObject_Type)

typedef struct {
    PyObject_HEAD

    PyObject *owner_pyobject; // Xine or VideoPort object
    int xine_object_owner;
    xine_t *xine;
    vo_driver_t *driver;

    PyObject *wrapper;

    void (*dealloc_cb)(void *);
    void *dealloc_data;
} Xine_VO_Driver_PyObject;

extern PyTypeObject Xine_VO_Driver_PyObject_Type;

PyObject *Xine_VO_Driver_PyObject__new(PyTypeObject *, PyObject *, PyObject *);
Xine_VO_Driver_PyObject *pyxine_new_vo_driver_pyobject(PyObject *, vo_driver_t *, int);


#endif
