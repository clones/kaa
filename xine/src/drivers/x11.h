#ifndef _X11_H_
#define _X11_H_

#include <Python.h>
#include <X11/X.h>
#include <X11/Xlib.h>
#include <X11/Xutil.h>
#include "../xine.h"
#include "common.h"

extern PyTypeObject *X11Window_PyObject_Type;
extern int (*x11window_object_decompose)(PyObject *, Window *, Display **);
int x11_get_visual_info(Xine_PyObject *xine, PyObject *kwargs, void **visual_return,
                        driver_info_common **driver_info_return);

#endif
