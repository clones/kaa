#ifndef _X11WINDOW_H_
#define _X11WINDOW_H_
#include <X11/Xlib.h>

typedef struct {
    PyObject_HEAD

    PyObject *display_pyobject;
    Display *display;
    Window   window;
    Cursor   invisible_cursor;

    PyObject *ptr;
} X11Window_PyObject;

extern PyTypeObject X11Window_PyObject_Type;

X11Window_PyObject *X11Window_PyObject__wrap(PyObject *display, Window window);
#endif
