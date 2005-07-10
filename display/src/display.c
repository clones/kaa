#include <Python.h>
#include "config.h"
#include "x11display.h"
#include "x11window.h"
#include "imlib2.h"
#include "evas.h"
#include "sdl.h"

PyMethodDef display_methods[] = {
    { "image_to_surface", image_to_surface, METH_VARARGS }, 
    { "render_imlib2_image", render_imlib2_image, METH_VARARGS }, 
    { "new_evas_software_x11", new_evas_software_x11, METH_VARARGS | METH_KEYWORDS }, 
#ifdef ENABLE_ENGINE_GL_X11
    { "new_evas_gl_x11", new_evas_gl_x11, METH_VARARGS | METH_KEYWORDS }, 
#endif
    { NULL }
};

void **get_module_api(char *module)
{
    PyObject *m, *c_api;
    void **ptrs;

    m = PyImport_ImportModule(module);
    if (m == NULL)
       return;
    c_api = PyObject_GetAttrString(m, "_C_API");
    if (c_api == NULL || !PyCObject_Check(c_api))
	   return;
    ptrs = (void **)PyCObject_AsVoidPtr(c_api);
    Py_DECREF(c_api);
    return ptrs;
}

void init_Display()
{
    PyObject *m, *display_c_api;
    void **imlib2_api_ptrs, *display_api_ptrs[1], **evas_api_ptrs;
    m = Py_InitModule("_Display", display_methods);

    if (PyType_Ready(&X11Display_PyObject_Type) < 0)
        return;
    Py_INCREF(&X11Display_PyObject_Type);
    PyModule_AddObject(m, "X11Display", (PyObject *)&X11Display_PyObject_Type);

    if (PyType_Ready(&X11Window_PyObject_Type) < 0)
        return;
    Py_INCREF(&X11Window_PyObject_Type);
    PyModule_AddObject(m, "X11Window", (PyObject *)&X11Window_PyObject_Type);

    // Export display C API
    display_api_ptrs[0] = (void *)X11Window_PyObject__wrap;
    display_c_api = PyCObject_FromVoidPtr((void *)display_api_ptrs, NULL);
    PyModule_AddObject(m, "_C_API", display_c_api);

#ifdef USE_IMLIB2
    // Import kaa-imlib2's C api
    imlib2_api_ptrs = get_module_api("kaa.imlib2._Imlib2");
    if (imlib2_api_ptrs == NULL)
	   return;
    imlib_image_from_pyobject = imlib2_api_ptrs[0];
    Image_PyObject_Type = imlib2_api_ptrs[1];
#else
    Image_PyObject_Type = NULL;
#endif

#ifdef USE_EVAS
    // Import kaa-evas's C api
    evas_api_ptrs = get_module_api("kaa.evas._evas");
    if (evas_api_ptrs == NULL)
	   return;
    evas_object_from_pyobject = evas_api_ptrs[0];
    Evas_PyObject_Type = evas_api_ptrs[1];
#else
    Evas_PyObject_Type = NULL;
#endif
}
