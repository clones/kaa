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


#if defined(ENABLE_ENGINE_SOFTWARE_X11) || defined(ENABLE_ENGINE_GL_X11)
#include <Evas.h>
Evas *(*evas_object_from_pyobject)(PyObject *pyevas);
PyTypeObject *Evas_PyObject_Type = NULL;
#endif

#ifdef ENABLE_ENGINE_SOFTWARE_X11
#include <Evas_Engine_Software_X11.h>
#endif

#ifdef ENABLE_ENGINE_GL_X11
#include <Evas_Engine_GL_X11.h>
#include <GL/gl.h>
#include <GL/glu.h>
#include <GL/glx.h>
#endif

#if defined(USE_IMLIB2_X11) && !defined(X_DISPLAY_MISSING)
#include <X11/Xlib.h>
#include <Imlib2.h>
Imlib_Image *(*imlib_image_from_pyobject)(PyObject *pyimg);
PyTypeObject *Image_PyObject_Type = NULL;
#endif



#if defined(ENABLE_ENGINE_SOFTWARE_X11) || defined(ENABLE_ENGINE_GL_X11)
X11Window_PyObject *
engine_common_x11_setup(Evas *evas, PyObject *kwargs,
                        X11Display_PyObject *disp,
    Visual *(*best_visual_get)(Display *, int),
    Colormap (*best_colormap_get)(Display *, int),
    int (*best_depth_get)(Display *, int),
    Display **ei_display, Drawable *ei_drawable, Visual **ei_visual,
    Colormap *ei_colormap, int *ei_depth)
{
    X11Window_PyObject *win_object, *py_parent;
    Window win, parent;
    XSetWindowAttributes attr;
    int screen, w, h;
    char *title = NULL;

    if (!PyArg_ParseTuple(PyDict_GetItemString(kwargs, "size"), "ii", &w, &h))
        return NULL;
    py_parent = (X11Window_PyObject *)PyDict_GetItemString(kwargs, "parent");
    if (PyMapping_HasKeyString(kwargs, "title"))
        title = PyString_AsString(PyDict_GetItemString(kwargs, "title"));

    if (py_parent) {
        parent = py_parent->window;
    }
    else
        parent = DefaultRootWindow(disp->display);

    attr.backing_store = NotUseful;
    attr.border_pixel = 0;
    attr.background_pixmap = None;
    attr.event_mask = ExposureMask | ButtonPressMask | ButtonReleaseMask |
        StructureNotifyMask | PointerMotionMask | KeyPressMask | FocusChangeMask;
    attr.bit_gravity = ForgetGravity;

    *ei_display = disp->display;
    XLockDisplay(*ei_display);
    screen = DefaultScreen(*ei_display);

    *ei_visual = best_visual_get(*ei_display, screen);
    *ei_colormap = attr.colormap = best_colormap_get(*ei_display, screen);
    *ei_depth = best_depth_get(*ei_display, screen);

    win = XCreateWindow(*ei_display, parent, 0, 0,
                        w, h, 0, *ei_depth, InputOutput, *ei_visual,
                        CWBackingStore | CWColormap | CWBackPixmap |
                        CWBitGravity | CWEventMask, &attr);

    *ei_drawable = win;
    if (title)
        XStoreName(*ei_display, win, title);
    XUnlockDisplay(*ei_display);

    win_object = X11Window_PyObject__wrap((PyObject *)disp, win);
    return win_object;
}

#define ENGINE_COMMON_X11_SETUP(evas, kwargs, display, func, info) \
    engine_common_x11_setup(evas, kwargs, display, \
        func.best_visual_get, func.best_colormap_get, func.best_depth_get, \
        &info.display, &info.drawable, &info.visual, &info.colormap, \
        &info.depth);


X11Window_PyObject *
new_evas_software_x11(PyObject *self, PyObject *args, PyObject *kwargs)
{
    Evas_Engine_Info_Software_X11 *einfo;
    X11Window_PyObject *x11;
    X11Display_PyObject *display;
    PyObject *evas_pyobject;
    Evas *evas;

    CHECK_EVAS_PYOBJECT

    if (!PyArg_ParseTuple(args, "O!O!", Evas_PyObject_Type, &evas_pyobject,
                        &X11Display_PyObject_Type, &display))
        return NULL;

    evas = evas_object_from_pyobject(evas_pyobject);
    evas_output_method_set(evas, evas_render_method_lookup("software_x11"));
    einfo = (Evas_Engine_Info_Software_X11 *)evas_engine_info_get(evas);
    if (!einfo) {
        PyErr_Format(PyExc_SystemError, "Evas is not built with Software X11 support.");
        return NULL;
    }

    x11 = ENGINE_COMMON_X11_SETUP(evas, kwargs, display, einfo->func,
                                  einfo->info);

    einfo->info.rotation = 0;
    einfo->info.debug = 0;

    evas_engine_info_set(evas, (Evas_Engine_Info *) einfo);
    return x11;
}

#ifdef ENABLE_ENGINE_GL_X11
X11Window_PyObject *
new_evas_gl_x11(PyObject *self, PyObject *args, PyObject *kwargs)
{
    Evas_Engine_Info_GL_X11 *einfo;
    X11Window_PyObject *x11;
    X11Display_PyObject *display;
    PyObject *evas_pyobject;
    Evas *evas;

    CHECK_EVAS_PYOBJECT

    if (!PyArg_ParseTuple(args, "O!O!", Evas_PyObject_Type, &evas_pyobject,
                        &X11Display_PyObject_Type, &display))
        return NULL;

    evas = evas_object_from_pyobject(evas_pyobject);

    evas_output_method_set(evas, evas_render_method_lookup("gl_x11"));
    einfo = (Evas_Engine_Info_GL_X11 *)evas_engine_info_get(evas);
    if (!einfo) {
        PyErr_Format(PyExc_SystemError, "Evas is not built with GLX support.");
        return NULL;
    }

    x11 = ENGINE_COMMON_X11_SETUP(evas, kwargs, display, einfo->func,
                                  einfo->info);
    evas_engine_info_set(evas, (Evas_Engine_Info *) einfo);
    return x11;
}
#endif

#endif  /* defined(ENABLE_ENGINE_GL_X11) ||
           defined (ENABLE_ENGINE_SOFTWARE_X11) */



#if defined(USE_IMLIB2_X11) && !defined(X_DISPLAY_MISSING)

PyObject *render_imlib2_image(PyObject *self, PyObject *args)
{
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
        imlib_render_image_part_on_drawable_at_size(src_x, src_y, w, h, dst_x,
                                dst_y, w, h);

    Py_INCREF(Py_None);
    return Py_None;
}
#else

PyObject *render_imlib2_image(PyObject *self, PyObject *args)
{
    PyErr_Format(PyExc_SystemError, "kaa-display compiled without imlib2 display support.");
    return NULL;
}

#endif

PyMethodDef display_methods[] = {
    { "render_imlib2_image", (PyCFunction) render_imlib2_image, METH_VARARGS },
#ifdef ENABLE_ENGINE_SOFTWARE_X11
    { "new_evas_software_x11", (PyCFunction) new_evas_software_x11, METH_VARARGS | METH_KEYWORDS },
#ifdef ENABLE_ENGINE_GL_X11
    { "new_evas_gl_x11", (PyCFunction) new_evas_gl_x11, METH_VARARGS | METH_KEYWORDS },
#endif
#endif
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

#if defined(ENABLE_ENGINE_SOFTWARE_X11) || defined(ENABLE_ENGINE_GL_X11)
{
    // Import kaa-evas's C api
    void **evas_api_ptrs = get_module_api("kaa.evas._evas");
    if (evas_api_ptrs != NULL) {
        evas_object_from_pyobject = evas_api_ptrs[0];
        Evas_PyObject_Type = evas_api_ptrs[1];
    } else
        PyErr_Clear();
}
#endif

    if (!XInitThreads())
        PyErr_Format(PyExc_SystemError, "Unable to initialize X11 threads.");
}

