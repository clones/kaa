#ifndef _IMLIB2_H_
#define _IMLIB2_H_

#include "config.h"
#include "display.h"

#ifndef USE_IMLIB2_DISPLAY
    #define X_DISPLAY_MISSING
#else
    #include <X11/Xlib.h>
#endif

#include <Imlib2.h>
extern Imlib_Image *(*imlib_image_from_pyobject)(PyObject *pyimg);

#endif

PyObject *render_imlib2_image(PyObject *self, PyObject *args);

