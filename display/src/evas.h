#include "config.h"

#ifndef _EVAS_H_
#define _EVAS_H_

#ifdef USE_EVAS
#include "x11window.h"
#include <Evas.h>
extern PyTypeObject *Evas_PyObject_Type;
extern Evas *(*evas_object_from_pyobject)(PyObject *pyevas);

X11Window_PyObject *new_evas_software_x11(PyObject *, PyObject *, PyObject *);

#ifdef ENABLE_ENGINE_GL_X11
X11Window_PyObject *new_evas_gl_x11(PyObject *, PyObject *, PyObject *);
#endif

#endif // USE_EVAS
#endif // _EVAS_H_
