#include <Python.h>
#define X_DISPLAY_MISSING
#include <Imlib2.h>
#include "config.h"

#ifdef USE_PYGAME
#include <pygame.h>
#endif

PyTypeObject *Image_PyObject_Type;
Imlib_Image (*imlib_image_from_pyobject)(PyObject *pyimg);

PyObject *image_to_surface(PyObject *self, PyObject *args)
{

#ifdef USE_PYGAME
    PyObject *pyimg;
    Imlib_Image *img;
    PySurfaceObject *pysurf;
    unsigned char *pixels;
    
    static int init = 0;

    if (init == 0) {
        import_pygame_surface();
	init = 1;
    }

    if (!PyArg_ParseTuple(args, "O!O!", Image_PyObject_Type, &pyimg, 
			  &PySurface_Type, &pysurf))
        return NULL;

    img  = imlib_image_from_pyobject(pyimg);
    imlib_context_set_image(img);
    pixels = (unsigned char *)imlib_image_get_data_for_reading_only();
    memcpy(pysurf->surf->pixels, pixels, imlib_image_get_width() * 
	   imlib_image_get_height() * 4);
    
    Py_INCREF(Py_None);
    return Py_None;

#else
    PyErr_Format(PyExc_SystemError, "kaa-display compiled without pygame");
    return NULL;
#endif

}
