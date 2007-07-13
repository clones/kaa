/*
 * ----------------------------------------------------------------------------
 * x11window.c
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
#include "x11window.h"
#include "x11display.h"
#include "structmember.h"

void _make_invisible_cursor(X11Window_PyObject *win);

int _ewmh_set_hint(X11Window_PyObject *o, char *type, void **data, int ndata)
{
    int res, i;
    XEvent ev;

    memset(&ev, 0, sizeof(ev));

    XLockDisplay(o->display);
    XUngrabPointer(o->display, CurrentTime);
    ev.xclient.type = ClientMessage;
    ev.xclient.send_event = True;
    ev.xclient.message_type = XInternAtom(o->display, type, False);
    ev.xclient.window = o->window;
    ev.xclient.format = 32;

    for (i = 0; i < ndata; i++)
        ev.xclient.data.l[i] = (long)data[i];
    res = XSendEvent(o->display, DefaultRootWindow(o->display), False,
                    SubstructureRedirectMask | SubstructureNotifyMask, &ev);
    XSync(o->display, False);
    XUnlockDisplay(o->display);

    return res;
}

static int
X11Window_PyObject__clear(X11Window_PyObject *self)
{
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
X11Window_PyObject__new(PyTypeObject *type, PyObject *args, PyObject *kwargs)
{
    X11Window_PyObject *self, *py_parent;
    X11Display_PyObject *display;
    Window parent;
    int w, h, screen;
    char *window_title = NULL;
    XSetWindowAttributes attr;

    self = (X11Window_PyObject *)type->tp_alloc(type, 0);
    if (!args)
        // args is NULL it means we're being called from __wrap()
        return (PyObject *)self;

    if (!PyArg_ParseTuple(args, "O!(ii)", &X11Display_PyObject_Type, &display, &w, &h))
        return NULL;

    py_parent = (X11Window_PyObject *)PyDict_GetItemString(kwargs, "parent");
    if (PyMapping_HasKeyString(kwargs, "title"))
        window_title = PyString_AsString(PyDict_GetItemString(kwargs, "title"));

    self->display_pyobject = (PyObject *)display;
    Py_INCREF(display);
    self->display = display->display;

    if (py_parent)
        parent = py_parent->window;
    else
        parent = DefaultRootWindow(self->display);

    XLockDisplay(self->display);

    if (PyMapping_HasKeyString(kwargs, "window")) {
        self->window = (Window)PyLong_AsUnsignedLong(PyDict_GetItemString(kwargs, "window"));
    } else {
        screen = DefaultScreen(self->display);
        attr.backing_store = NotUseful;
        attr.border_pixel = 0;
        attr.background_pixmap = None;
        attr.event_mask = ExposureMask | ButtonPressMask | ButtonReleaseMask |
            StructureNotifyMask | PointerMotionMask | KeyPressMask | FocusChangeMask;
        attr.bit_gravity = StaticGravity;
        attr.win_gravity = StaticGravity;
        attr.override_redirect = False;
        attr.colormap = DefaultColormap(self->display, screen);

        self->window = XCreateWindow(self->display, parent, 0, 0,
                            w, h, 0, DefaultDepth(self->display, screen), InputOutput,
                            DefaultVisual(self->display, screen),
                            CWBackingStore | CWColormap | CWBackPixmap | CWWinGravity |
                            CWBitGravity | CWEventMask | CWOverrideRedirect, &attr);

        if (window_title)
            XStoreName(self->display, self->window, window_title);
    }
    self->wid = PyLong_FromUnsignedLong(self->window);
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
    printf("X11Window dealloc\n");
    if (self->window) {
        XLockDisplay(self->display);
        XDestroyWindow(self->display, self->window);
        Py_XDECREF(self->wid);
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
    int raise;
    if (!PyArg_ParseTuple(args, "i", &raise))
        return NULL;

    XLockDisplay(self->display);
    if (raise)
        XMapRaised(self->display, self->window);
    else
        XMapWindow(self->display, self->window);
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
X11Window_PyObject__raise(X11Window_PyObject * self, PyObject * args)
{
    XLockDisplay(self->display);
    XRaiseWindow(self->display, self->window);
    XSync(self->display, False);
    XUnlockDisplay(self->display);
    return Py_INCREF(Py_None), Py_None;
}


PyObject *
X11Window_PyObject__lower(X11Window_PyObject * self, PyObject * args)
{
    XLockDisplay(self->display);
    XLowerWindow(self->display, self->window);
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
    return PyBool_FromLong(_ewmh_set_hint(self, "_NET_WM_STATE", data, 2));
}

PyObject *
X11Window_PyObject__set_transient_for_hint(X11Window_PyObject *self, PyObject *args)
{
    int win_id, transient;

    if (!PyArg_ParseTuple(args, "ii", &win_id, &transient))
        return NULL;

    XLockDisplay(self->display);
    XUngrabPointer(self->display, CurrentTime);
    if (!transient)
    {
        XDeleteProperty(self->display, self->window, XA_WM_TRANSIENT_FOR);
    } else
    {
        if (!win_id)
        {
            win_id = DefaultRootWindow(self->display);
        }
        XSetTransientForHint(self->display, self->window, win_id);
    }
    XSync(self->display, False);
    XUnlockDisplay(self->display);
    return PyBool_FromLong((long) transient);
}

PyObject *
X11Window_PyObject__get_visible(X11Window_PyObject * self, PyObject * args)
{
    XWindowAttributes attrs;
    XLockDisplay(self->display);
    XGetWindowAttributes(self->display, self->window, &attrs);
    XUnlockDisplay(self->display);
    return Py_BuildValue("i", attrs.map_state);
}

PyObject *
X11Window_PyObject__focus(X11Window_PyObject * self, PyObject * args)
{
    XLockDisplay(self->display);
    XSetInputFocus(self->display, self->window, RevertToParent, CurrentTime);
    XUnlockDisplay(self->display);
    Py_INCREF(Py_None);
    return Py_None;
}


PyMethodDef X11Window_PyObject_methods[] = {
    { "show", (PyCFunction)X11Window_PyObject__show, METH_VARARGS },
    { "hide", (PyCFunction)X11Window_PyObject__hide, METH_VARARGS },
    { "raise_window", (PyCFunction)X11Window_PyObject__raise, METH_VARARGS },
    { "lower_window", (PyCFunction)X11Window_PyObject__lower, METH_VARARGS },
    { "set_geometry", (PyCFunction)X11Window_PyObject__set_geometry, METH_VARARGS },
    { "get_geometry", (PyCFunction)X11Window_PyObject__get_geometry, METH_VARARGS },
    { "set_cursor_visible", (PyCFunction)X11Window_PyObject__set_cursor_visible, METH_VARARGS },
    { "set_fullscreen", (PyCFunction)X11Window_PyObject__set_fullscreen, METH_VARARGS },
    { "set_transient_for", (PyCFunction)X11Window_PyObject__set_transient_for_hint, METH_VARARGS },
    { "get_visible", (PyCFunction)X11Window_PyObject__get_visible, METH_VARARGS },
    { "focus", (PyCFunction)X11Window_PyObject__focus, METH_VARARGS },
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
    o->wid = PyLong_FromUnsignedLong(window);
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
    if (!win || !X11Window_PyObject_Check(win))
        return 0;

    if (window)
        *window = win->window;
    if (display)
        *display = win->display;

    return 1;
}


static PyMemberDef X11Window_PyObject_members[] = {
    {"wid", T_OBJECT_EX, offsetof(X11Window_PyObject, wid), 0, ""},
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
