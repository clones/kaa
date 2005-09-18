#ifndef _X11_H_
#define _X11_H_

#include <Python.h>
#include <X11/X.h>
#include <X11/Xlib.h>
#include <X11/Xutil.h>
#include "../xine.h"
#include "../vo_driver.h"

extern PyTypeObject *X11Window_PyObject_Type;
extern int (*x11window_object_decompose)(PyObject *, Window *, Display **);
Xine_VO_Driver_PyObject *x11_open_video_driver(Xine_PyObject *, char *, PyObject *kwargs);

#endif
