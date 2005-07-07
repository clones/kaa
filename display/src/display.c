#include <Python.h>
#define X_DISPLAY_MISSING
#include <Imlib2.h>
#include "sdl.h"

PyTypeObject *Image_PyObject_Type;
Imlib_Image (*imlib_image_from_pyobject)(PyObject *pyimg);

PyMethodDef Imlib2_methods[] = {
    { "image_to_surface", image_to_surface, METH_VARARGS }, 
    { NULL }
};

void init_Display()
{
    PyObject *m, *pyimlib2_module, *c_api;
    void **api_ptrs;
    m = Py_InitModule("_Display", Imlib2_methods);

    pyimlib2_module = PyImport_ImportModule("kaa.imlib2._Imlib2");
    if (pyimlib2_module == NULL)
       return;

    c_api = PyObject_GetAttrString(pyimlib2_module, "_C_API");
    if (c_api == NULL || !PyCObject_Check(c_api))
	   return;
    api_ptrs = (void **)PyCObject_AsVoidPtr(c_api);
    Py_DECREF(c_api);
    imlib_image_from_pyobject = api_ptrs[0];
    Image_PyObject_Type = api_ptrs[1];
}
