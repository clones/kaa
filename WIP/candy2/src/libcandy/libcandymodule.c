#ifdef HAVE_CONFIG_H
#include "config.h"
#endif

#include <pygobject.h>
#include <clutter/clutter.h>
#include "libcandy.h"

void libcandy_register_classes (PyObject *d);
extern PyMethodDef libcandy_functions[];

DL_EXPORT (void)
initlibcandy (void)
{
        PyObject *m, *d;

        init_pygobject ();

        if (PyImport_ImportModule ("clutter") == NULL) {
                PyErr_SetString (PyExc_ImportError,
                                 "could not import clutter");
                return;
        }

        m = Py_InitModule ("libcandy", libcandy_functions);
        d = PyModule_GetDict (m);

        libcandy_register_classes (d);

        if (PyErr_Occurred ()) {
                Py_FatalError ("unable to initialise libcandy module");
        }
}
