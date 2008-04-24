/*
 * ----------------------------------------------------------------------------
 * x11window.h
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

#ifndef _X11WINDOW_H_
#define _X11WINDOW_H_

#include <X11/X.h>
#include <X11/Xlib.h>
#include <X11/Xatom.h>
#include <X11/extensions/shape.h>
#include <stdint.h>

#define X11Window_PyObject_Check(v) ((v)->ob_type == &X11Window_PyObject_Type)

typedef struct {
    PyObject_HEAD

    PyObject *display_pyobject;
    Display *display;
    Window   window;
    Cursor   invisible_cursor;

    PyObject *wid;
    int owner;
} X11Window_PyObject;

extern PyTypeObject X11Window_PyObject_Type;

// Exported API functions
int x11window_object_decompose(X11Window_PyObject *, Window *, Display **);
X11Window_PyObject *X11Window_PyObject__wrap(PyObject *display, Window window);

// EWMH state actions: http://freedesktop.org/Standards/wm-spec/index.html
#define _NET_WM_STATE_REMOVE    0
#define _NET_WM_STATE_ADD       1
#define _NET_WM_STATE_TOGGLE    2

#endif
