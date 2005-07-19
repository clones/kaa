#ifndef _X11_H_
#define _X11_H_

#include <Python.h>
#include <X11/X.h>
#include <X11/Xlib.h>
#include <X11/Xutil.h>
#include "../xine.h"
#include "../video_port.h"

extern PyTypeObject *X11Window_PyObject_Type;
extern int (*x11window_object_decompose)(PyObject *, Window *, Display **);
xine_video_port_t *x11_open_video_driver(Xine_PyObject *, char *, PyObject *kwargs, void **);
void x11_open_video_driver_finalize(Xine_Video_Port_PyObject *, void *);

#endif
