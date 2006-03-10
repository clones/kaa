/*
 * ----------------------------------------------------------------------------
 * sdl.c - Imlib2 to Pygame
 * ----------------------------------------------------------------------------
 * $Id$
 *
 * ----------------------------------------------------------------------------
 * kaa-display - Generic Display Module
 * Copyright (C) 2005 Dirk Meyer, Jason Tackaberry
 *
 * First Edition: Dirk Meyer <dmeyer@tzi.de>
 * Maintainer:    Dirk Meyer <dmeyer@tzi.de>
 *
 * Please see the file AUTHORS for a complete list of authors.
 *
 * This program is free software; you can redistribute it and/or modify
 * it under the terms of the GNU General Public License as published by
 * the Free Software Foundation; either version 2 of the License, or
 * (at your option) any later version.
 *
 * This program is distributed in the hope that it will be useful, but
 * WITHOUT ANY WARRANTY; without even the implied warranty of MER-
 * CHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the GNU General
 * Public License for more details.
 *
 * You should have received a copy of the GNU General Public License along
 * with this program; if not, write to the Free Software Foundation, Inc.,
 * 59 Temple Place, Suite 330, Boston, MA 02111-1307 USA
 *
 * ----------------------------------------------------------------------------
 */

#include <pygame.h>

#include "config.h"
#include <Python.h>

#include "imlib2.h"

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


PyMethodDef sdl_methods[] = {
    { "image_to_surface", (PyCFunction) image_to_surface, METH_VARARGS },
    { NULL }
};


void **get_module_api(char *module)
{
    PyObject *m, *c_api;
    void **ptrs;

    m = PyImport_ImportModule(module);
    if (m == NULL)
       return NULL;
    c_api = PyObject_GetAttrString(m, "_C_API");
    if (c_api == NULL || !PyCObject_Check(c_api))
        return NULL;
    ptrs = (void **)PyCObject_AsVoidPtr(c_api);
    Py_DECREF(c_api);
    return ptrs;
}

void init_SDL()
{
    void **imlib2_api_ptrs;

    Py_InitModule("_SDL", sdl_methods);

    // Import kaa-imlib2's C api
    imlib2_api_ptrs = get_module_api("kaa.imlib2._Imlib2");
    if (imlib2_api_ptrs == NULL)
        return;
    imlib_image_from_pyobject = imlib2_api_ptrs[0];
    Image_PyObject_Type = imlib2_api_ptrs[1];
}
