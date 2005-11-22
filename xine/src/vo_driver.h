#ifndef __VO_DRIVER_H_
#define __VO_DRIVER_H_
#include "config.h"

#include <Python.h>
#include <xine.h>
#include <xine/video_out.h>
#include "drivers/common.h"

#define Xine_VO_Driver_PyObject_Check(v) ((v)->ob_type == &Xine_VO_Driver_PyObject_Type)

typedef struct {
    PyObject_HEAD

    Xine_PyObject *xine;
    vo_driver_t *driver;
    void *owner; // Xine or VideoPort object
    int do_dispose;

    PyObject *wrapper;

    driver_info_common *driver_info;
} Xine_VO_Driver_PyObject;

extern PyTypeObject Xine_VO_Driver_PyObject_Type;

PyObject *Xine_VO_Driver_PyObject__new(PyTypeObject *, PyObject *, PyObject *);
Xine_VO_Driver_PyObject *pyxine_new_vo_driver_pyobject(Xine_PyObject *, void *, vo_driver_t *, int);


#endif
