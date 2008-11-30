/*
 * ----------------------------------------------------------------------------
 * x11.c
 * ----------------------------------------------------------------------------
 * $Id$
 *
 * ----------------------------------------------------------------------------
 * kaa.display - Generic Display Module
 * Copyright (C) 2005, 2006 Dirk Meyer, Jason Tackaberry
 *
 * First Edition: Jason Tackaberry <tack@sault.org>
 * Maintainer:    Jason Tackaberry <tack@sault.org>
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

#include <Python.h>
#include "config.h"
#include "x11display.h"
#include "x11window.h"
#include "common.h"


#if defined(USE_IMLIB2_X11) && !defined(X_DISPLAY_MISSING)
#include <X11/Xlib.h>
#include <Imlib2.h>
Imlib_Image *(*imlib_image_from_pyobject)(PyObject *pyimg);
PyTypeObject *Image_PyObject_Type = NULL;
#endif


PyObject *render_imlib2_image(PyObject *self, PyObject *args)
{
#if defined(USE_IMLIB2_X11) && !defined(X_DISPLAY_MISSING)
    X11Window_PyObject *window;
    PyObject *pyimg;
    Imlib_Image *img;
    XWindowAttributes attrs;
    int dst_x = 0, dst_y = 0, src_x = 0, src_y = 0,
        w = -1, h = -1, img_w, img_h, dither = 1, blend = 0;

    CHECK_IMAGE_PYOBJECT

    if (!PyArg_ParseTuple(args, "O!O!|(ii)(ii)(ii)ii",
                &X11Window_PyObject_Type, &window,
                Image_PyObject_Type, &pyimg,
                &dst_x, &dst_y, &src_x, &src_y, &w, &h,
                &dither, &blend))
        return NULL;

    img = imlib_image_from_pyobject(pyimg);
    imlib_context_set_image(img);
    img_w = imlib_image_get_width();
    img_h = imlib_image_get_height();

    if (w == -1) w = img_w;
    if (h == -1) h = img_h;

    XGetWindowAttributes(window->display, window->window, &attrs);
    imlib_context_set_display(window->display);
    imlib_context_set_visual(attrs.visual);
    imlib_context_set_colormap(attrs.colormap);
    imlib_context_set_drawable(window->window);

    imlib_context_set_dither(dither);
    imlib_context_set_blend(blend);
    if (src_x == 0 && src_y == 0 && w == img_w && h == img_h)
        imlib_render_image_on_drawable(dst_x, dst_y);
    else
        imlib_render_image_part_on_drawable_at_size(src_x, src_y, w, h, dst_x, dst_y, w, h);

    Py_INCREF(Py_None);
    return Py_None;
#else
    PyErr_Format(PyExc_SystemError, "kaa-display compiled without imlib2 display support.");
    return NULL;
#endif
}


PyObject *set_shape_mask_from_imlib2_image(PyObject *self, PyObject *args)
{
#if defined(USE_IMLIB2_X11) && !defined(X_DISPLAY_MISSING)
    X11Window_PyObject *window;
    PyObject *pyimg;
    Imlib_Image *img;
    int x = 0, y = 0, threshold;
    XWindowAttributes attrs;
    Pixmap image_pixmap, mask_pixmap;
    
    CHECK_IMAGE_PYOBJECT

    if (!PyArg_ParseTuple(args, "O!O!|(ii)i",
                &X11Window_PyObject_Type, &window,
                Image_PyObject_Type, &pyimg,
                &x, &y, &threshold))
        return NULL;

    img = imlib_image_from_pyobject(pyimg);
    
    XGetWindowAttributes(window->display, window->window, &attrs);
    
    imlib_context_set_display(window->display);
    imlib_context_set_drawable(window->window);
    imlib_context_set_visual(attrs.visual);
    imlib_context_set_colormap(attrs.colormap);    
    
    imlib_context_set_image(img);
    imlib_context_set_mask_alpha_threshold(threshold);
    
    imlib_render_pixmaps_for_whole_image(&image_pixmap, &mask_pixmap);
    if (mask_pixmap != None) {
        XShapeCombineMask(window->display, window->window, ShapeBounding, x, y, mask_pixmap, ShapeSet);
        imlib_free_pixmap_and_mask(image_pixmap);
    }
    
    Py_INCREF(Py_None);
    return Py_None;
#else
    PyErr_Format(PyExc_SystemError, "kaa-display compiled without imlib2 display support.");
    return NULL;
#endif
}

PyMethodDef display_methods[] = {
    { "render_imlib2_image", (PyCFunction) render_imlib2_image, METH_VARARGS },
    { "set_shape_mask_from_imlib2_image", (PyCFunction) set_shape_mask_from_imlib2_image, METH_VARARGS },
    { NULL }
};

void init_X11(void)
{
    PyObject *m, *display_c_api;
    static void *display_api_ptrs[3];

    m = Py_InitModule("_X11", display_methods);

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
    display_api_ptrs[1] = (void *)&X11Window_PyObject_Type;
    display_api_ptrs[2] = (void *)x11window_object_decompose;

    display_c_api = PyCObject_FromVoidPtr((void *)display_api_ptrs, NULL);
    PyModule_AddObject(m, "_C_API", display_c_api);

#if defined(USE_IMLIB2_X11) && !defined(X_DISPLAY_MISSING)
{
    // Import kaa-imlib2's C api
    void **imlib2_api_ptrs = get_module_api("kaa.imlib2._Imlib2");
    if (imlib2_api_ptrs != NULL) {
        imlib_image_from_pyobject = imlib2_api_ptrs[0];
        Image_PyObject_Type = imlib2_api_ptrs[1];
    } else
        PyErr_Clear();
}
#endif

    if (!XInitThreads())
        PyErr_Format(PyExc_SystemError, "Unable to initialize X11 threads.");
}

