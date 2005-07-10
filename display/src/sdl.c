#include "config.h"
#include <Python.h>

#if defined(USE_PYGAME) && defined(USE_IMLIB2)
#include "imlib2.h"
#include <pygame.h>

PyObject *image_to_surface(PyObject *self, PyObject *args)
{

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
}
#else

PyObject *image_to_surface(PyObject *self, PyObject *args)
{
    PyErr_Format(PyExc_SystemError, "kaa-display compiled without pygame and/or imlib2");
    return NULL;
}
#endif
