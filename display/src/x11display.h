#ifndef _X11DISPLAY_H_
#define _X11DISPLAY_H_
#include <X11/Xlib.h>

typedef struct {
    PyObject_HEAD

    Display *display;
    PyObject *socket;
} X11Display_PyObject;

extern PyTypeObject X11Display_PyObject_Type;
#endif
