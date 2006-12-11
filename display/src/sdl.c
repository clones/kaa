/*
 * ----------------------------------------------------------------------------
 * sdl.c - Imlib2 to Pygame
 * ----------------------------------------------------------------------------
 * $Id$
 *
 * ----------------------------------------------------------------------------
 * kaa.display - Generic Display Module
 * Copyright (C) 2005, 2006 Dirk Meyer, Jason Tackaberry
 *
 * First Edition: Dirk Meyer <dmeyer@tzi.de>
 * Maintainer:    Dirk Meyer <dmeyer@tzi.de>
 *
 * Please see the file AUTHORS for a complete list of authors.
 *
 * This library is free software; you can redistribute it and/or modify
 * it under the terms of the GNU Lesser General Public License version
 * 2.1 as published by the Free Software Foundation.
 *
 * This library is distributed in the hope that it will be useful, but
 * WITHOUT ANY WARRANTY; without even the implied warranty of
 * MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
 * Lesser General Public License for more details.
 *
 * You should have received a copy of the GNU Lesser General Public
 * License along with this library; if not, write to the Free Software
 * Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA
 * 02110-1301 USA
 *
 * ----------------------------------------------------------------------------
 */

#include <pygame.h>

#include "config.h"
#include <Python.h>
#include "common.h"

#define X_DISPLAY_MISSING
#include <Imlib2.h>
Imlib_Image *(*imlib_image_from_pyobject)(PyObject *pyimg);
PyTypeObject *Image_PyObject_Type = NULL;

PyObject *image_to_surface(PyObject *self, PyObject *args)
{
    PyObject *pyimg;
    Imlib_Image *img;
    PySurfaceObject *pysurf;
    unsigned char *pixels;

    static int init = 0;

    CHECK_IMAGE_PYOBJECT

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


void init_SDL(void)
{
    void **imlib2_api_ptrs;

    Py_InitModule("_SDL", sdl_methods);

    // Import kaa-imlib2's C api
    imlib2_api_ptrs = get_module_api("kaa.imlib2._Imlib2");
    if (imlib2_api_ptrs != NULL) {
        imlib_image_from_pyobject = imlib2_api_ptrs[0];
        Image_PyObject_Type = imlib2_api_ptrs[1];
    } else
        PyErr_Clear();
}
