/*
 * ----------------------------------------------------------------------------
 * x11window.c
 * ----------------------------------------------------------------------------
 * $Id$
 *
 * ----------------------------------------------------------------------------
 * kaa-display - X11/SDL Display module
 * Copyright (C) 2005 Dirk Meyer, Jason Tackaberry
 *
 * First Edition: Jason Tackaberry <tack@sault.org>
 * Maintainer:    Jason Tackaberry <tack@sault.org>
 *
 * Please see the file doc/CREDITS for a complete list of authors.
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

#include <Python.h>
#include "x11window.h"
#include "x11display.h"
#include "structmember.h"

void _make_invisible_cursor(X11Window_PyObject *win);

int _ewmh_set_hint(X11Window_PyObject *o, char *type, void **data)
{
    int res, i;
    XEvent ev;

    memset(&ev, 0, sizeof(ev));

    XLockDisplay(o->display);
    ev.xclient.type = ClientMessage;
    ev.xclient.send_event = True;
    ev.xclient.message_type = XInternAtom(o->display, type, False);
    ev.xclient.window = o->window;
    ev.xclient.format = 32;

    for (i = 0; data && data[i]; i++)
        ev.xclient.data.l[i] = (long)data[i];
    res = XSendEvent(o->display, DefaultRootWindow(o->display), False,
                    SubstructureRedirectMask | SubstructureNotifyMask, &ev);
    XUnlockDisplay(o->display);

    return res;
}

static int
X11Window_PyObject__clear(X11Window_PyObject *self)
{
    PyObject *tmp;
    if (self->display_pyobject) {
        tmp = self->display_pyobject;
        self->display_pyobject = 0;
        Py_DECREF(tmp);
    }
    return 0;
}


static int
X11Window_PyObject__traverse(X11Window_PyObject *self, visitproc visit,
                             void *arg)
{
    int ret;
    if (self->display_pyobject) {
        ret = visit(self->display_pyobject, arg);
        if (ret != 0)
            return ret;
    }
    return 0;
}

PyObject *
X11Window_PyObject__new(PyTypeObject *type, PyObject * args, PyObject * kwargs)
{
    X11Window_PyObject *self;
    X11Display_PyObject *display;
    int w, h;
    char *window_title;

    self = (X11Window_PyObject *)type->tp_alloc(type, 0);
    if (!args)
        // args is NULL it means we're being called from __wrap()
        return (PyObject *)self;

    if (!PyArg_ParseTuple(args, "O!(ii)s", &X11Display_PyObject_Type, &display,
                          &w, &h, &window_title))
        return NULL;

    self->display_pyobject = (PyObject *)display;
    Py_INCREF(display);
    self->display = display->display;
    XLockDisplay(self->display);
    self->window = XCreateSimpleWindow(self->display,
            DefaultRootWindow(self->display), 0, 0, w, h, 0, 0, 0);
    XStoreName(self->display, self->window, window_title);
    XSelectInput(self->display, self->window, ExposureMask | KeyPressMask |
                 PointerMotionMask);
    self->ptr = PyInt_FromLong(self->window);
    _make_invisible_cursor(self);
    XUnlockDisplay(self->display);
    return (PyObject *)self;
}

static int
X11Window_PyObject__init(X11Window_PyObject *self, PyObject *args,
                         PyObject *kwds)
{
    return 0;
}

void
X11Window_PyObject__dealloc(X11Window_PyObject * self)
{
    if (self->window) {
        //printf("X11Window destroy\n");
        XLockDisplay(self->display);
        XDestroyWindow(self->display, self->window);
        Py_XDECREF(self->ptr);
        XFreeCursor(self->display, self->invisible_cursor);
        XUnlockDisplay(self->display);
    }
    Py_XDECREF(self->display_pyobject);
    X11Window_PyObject__clear(self);
    self->ob_type->tp_free((PyObject*)self);
}


PyObject *
X11Window_PyObject__show(X11Window_PyObject * self, PyObject * args)
{
    XLockDisplay(self->display);
    XMapRaised(self->display, self->window);
    XSync(self->display, False);
    XUnlockDisplay(self->display);
    return Py_INCREF(Py_None), Py_None;
}

PyObject *
X11Window_PyObject__hide(X11Window_PyObject * self, PyObject * args)
{
    XLockDisplay(self->display);
    XUnmapWindow(self->display, self->window);
    XSync(self->display, False);
    XUnlockDisplay(self->display);
    return Py_INCREF(Py_None), Py_None;
}

PyObject *
X11Window_PyObject__set_geometry(X11Window_PyObject * self, PyObject * args)
{
    int x, y;
    unsigned int w, h;
    if (!PyArg_ParseTuple(args, "(ii)(ii)", &x, &y, &w, &h))
        return NULL;

    XLockDisplay(self->display);
    if (x != -1 && w != -1)
        XMoveResizeWindow(self->display, self->window, x, y, w, h);
    else if (x != -1)
        XMoveWindow(self->display, self->window, x, y);
    else if (w != -1)
        XResizeWindow(self->display, self->window, w, h);

    XSync(self->display, False);
    XUnlockDisplay(self->display);
    return Py_INCREF(Py_None), Py_None;
}

PyObject *
X11Window_PyObject__set_cursor_visible(X11Window_PyObject *self, PyObject *args)
{
    int visible;
    if (!PyArg_ParseTuple(args, "i", &visible))
        return NULL;

    XLockDisplay(self->display);
    if (!visible)
        XDefineCursor(self->display, self->window, self->invisible_cursor);
    else
        XUndefineCursor(self->display, self->window);
    XUnlockDisplay(self->display);

    return Py_INCREF(Py_None), Py_None;
}

PyObject *
X11Window_PyObject__get_geometry(X11Window_PyObject * self, PyObject * args)
{
    XWindowAttributes attrs;
    XLockDisplay(self->display);
    XGetWindowAttributes(self->display, self->window, &attrs);
    XUnlockDisplay(self->display);
    return Py_BuildValue("((ii)(ii))", attrs.x, attrs.y, attrs.width,
                         attrs.height);
}

PyObject *
X11Window_PyObject__set_fullscreen(X11Window_PyObject *self, PyObject *args)
{
    int fs;
    void *data[3];

    if (!PyArg_ParseTuple(args, "i", &fs))
        return NULL;

    data[0] = (void *)(fs ? _NET_WM_STATE_ADD : _NET_WM_STATE_REMOVE);
    data[1] = (void *)XInternAtom(self->display, "_NET_WM_STATE_FULLSCREEN", False);
    data[2] = NULL;
    return PyBool_FromLong(_ewmh_set_hint(self, "_NET_WM_STATE", data));
}

PyMethodDef X11Window_PyObject_methods[] = {
    { "show", (PyCFunction)X11Window_PyObject__show, METH_VARARGS },
    { "hide", (PyCFunction)X11Window_PyObject__hide, METH_VARARGS },
    { "set_geometry", (PyCFunction)X11Window_PyObject__set_geometry, METH_VARARGS },
    { "get_geometry", (PyCFunction)X11Window_PyObject__get_geometry, METH_VARARGS },
    { "set_cursor_visible", (PyCFunction)X11Window_PyObject__set_cursor_visible, METH_VARARGS },
    { "set_fullscreen", (PyCFunction)X11Window_PyObject__set_fullscreen, METH_VARARGS },
    { NULL, NULL }
};


X11Window_PyObject *
X11Window_PyObject__wrap(PyObject *display, Window window)
{
    X11Window_PyObject *o;

    o = (X11Window_PyObject *)X11Window_PyObject__new(&X11Window_PyObject_Type,
                                                      NULL, NULL);

    o->display_pyobject = display;
    Py_INCREF(display);
    o->display = ((X11Display_PyObject *)display)->display;
    o->window = window;
    o->ptr = PyInt_FromLong(window);
    XLockDisplay(o->display);
    _make_invisible_cursor(o);
    XUnlockDisplay(o->display);
    return o;
}

void
_make_invisible_cursor(X11Window_PyObject *win)
{
    Pixmap pix;
    static char bits[] = {0, 0, 0, 0, 0, 0, 0};
    XColor cfg;

    // Construct an invisible cursor for mouse hiding.
    cfg.red = cfg.green = cfg.blue = 0;
    pix = XCreateBitmapFromData(win->display, win->window, bits, 1, 1);
    // Memory leak in Xlib: https://bugs.freedesktop.org/show_bug.cgi?id=3568
    win->invisible_cursor = XCreatePixmapCursor(win->display, pix, pix, &cfg,
                                                &cfg, 0, 0);
    XFreePixmap(win->display, pix);
}

// Exported _C_API function
int x11window_object_decompose(X11Window_PyObject *win, Window *window, Display **display)
{
    XWindowAttributes attrs;

    if (!win || !X11Window_PyObject_Check(win))
        return 0;

    if (window)
        *window = win->window;
    if (display)
        *display = win->display;

    return 1;
}


static PyMemberDef X11Window_PyObject_members[] = {
    {"ptr", T_OBJECT_EX, offsetof(X11Window_PyObject, ptr), 0, ""},
    {NULL}  /* Sentinel */
};


PyTypeObject X11Window_PyObject_Type = {
    PyObject_HEAD_INIT(NULL)
    0,                         /*ob_size*/
    "X11Window",              /*tp_name*/
    sizeof(X11Window_PyObject),  /*tp_basicsize*/
    0,                         /*tp_itemsize*/
    (destructor)X11Window_PyObject__dealloc, /* tp_dealloc */
    0,                         /*tp_print*/
    0,                         /* tp_getattr */
    0,                         /* tp_setattr */
    0,                         /*tp_compare*/
    0,                         /*tp_repr*/
    0,                         /*tp_as_number*/
    0,                         /*tp_as_sequence*/
    0,                         /*tp_as_mapping*/
    0,                         /*tp_hash */
    0,                         /*tp_call*/
    0,                         /*tp_str*/
    PyObject_GenericGetAttr,   /*tp_getattro*/
    PyObject_GenericSetAttr,   /*tp_setattro*/
    0,                         /*tp_as_buffer*/
    Py_TPFLAGS_DEFAULT | Py_TPFLAGS_BASETYPE | Py_TPFLAGS_HAVE_GC, /*tp_flags*/
    "X11 Window Object",      /* tp_doc */
    (traverseproc)X11Window_PyObject__traverse,   /* tp_traverse */
    (inquiry)X11Window_PyObject__clear,           /* tp_clear */
    0,                     /* tp_richcompare */
    0,                     /* tp_weaklistoffset */
    0,                     /* tp_iter */
    0,                     /* tp_iternext */
    X11Window_PyObject_methods,             /* tp_methods */
    X11Window_PyObject_members,             /* tp_members */
    0,                         /* tp_getset */
    0,                         /* tp_base */
    0,                         /* tp_dict */
    0,                         /* tp_descr_get */
    0,                         /* tp_descr_set */
    0,                         /* tp_dictoffset */
    (initproc)X11Window_PyObject__init,      /* tp_init */
    0,                         /* tp_alloc */
    X11Window_PyObject__new,   /* tp_new */
};
