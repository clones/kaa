/*
 * ----------------------------------------------------------------------------
 * evas.c
 * ----------------------------------------------------------------------------
 * $Id$
 *
 * ----------------------------------------------------------------------------
 * kaa-display - Generic Display Module
 * Copyright (C) 2005 Dirk Meyer, Jason Tackaberry
 *
 * First Edition: Jason Tackaberry <tack@sault.org>
 * Maintainer:    Jason Tackaberry <tack@sault.org>
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

#include "config.h"
#include <Python.h>

PyTypeObject *Evas_PyObject_Type;


#ifdef USE_EVAS

#include "evas.h"
#include "x11display.h"
#include "x11window.h"

Evas *(*evas_object_from_pyobject)(PyObject *pyevas);

#if defined(ENABLE_ENGINE_GL_X11) || defined (ENABLE_ENGINE_SOFTWARE_X11)
#ifdef ENABLE_ENGINE_SOFTWARE_X11
#include <Evas_Engine_Software_X11.h>
#endif

#ifdef ENABLE_ENGINE_GL_X11
#include <Evas_Engine_GL_X11.h>
#include <GL/gl.h>
#include <GL/glu.h>
#include <GL/glx.h>
#endif

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

    *ei_display = disp->display; //XOpenDisplay(XDisplayString(disp->display));
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

    if (!PyArg_ParseTuple(args, "O!O!", Evas_PyObject_Type, &evas_pyobject,
                        &X11Display_PyObject_Type, &display))
        return NULL;

    evas = evas_object_from_pyobject(evas_pyobject);
    evas_output_method_set(evas, evas_render_method_lookup("software_x11"));
    einfo = (Evas_Engine_Info_Software_X11 *)evas_engine_info_get(evas);

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

    if (!PyArg_ParseTuple(args, "O!O!", Evas_PyObject_Type, &evas_pyobject,
                        &X11Display_PyObject_Type, &display))
        return NULL;

    evas = evas_object_from_pyobject(evas_pyobject);

    evas_output_method_set(evas, evas_render_method_lookup("gl_x11"));
    einfo = (Evas_Engine_Info_GL_X11 *)evas_engine_info_get(evas);
    if (!einfo) {
        PyErr_Format(PyExc_SystemError, "Unable to initialize GL canvas");
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
#endif  // USE_EVAS
