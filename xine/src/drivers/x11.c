#include "x11.h"

PyTypeObject *X11Window_PyObject_Type;
int (*x11window_object_decompose)(PyObject *, Window *, Display **);

