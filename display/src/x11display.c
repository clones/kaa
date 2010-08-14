/*
 * ----------------------------------------------------------------------------
 * x11display.c
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

#include "config.h"

#include <Python.h>
#include <X11/Xlib.h>
#include <X11/Xutil.h>
#ifdef ENABLE_ENGINE_GL_X11
#include <GL/glx.h>
#endif
#ifdef HAVE_X11_COMPOSITE
#include <X11/extensions/Xcomposite.h>
#endif

#include "x11display.h"
#include "structmember.h"


extern PyTypeObject X11Display_PyObject_Type;


PyObject *
X11Display_PyObject__new(PyTypeObject *type, PyObject * args,
                         PyObject * kwargs)
{
    X11Display_PyObject *self;
    Display *display;
    char *display_name;
    if (!PyArg_ParseTuple(args, "s", &display_name))
        return NULL;
    if (strlen(display_name) == 0)
        display_name = NULL;

    display = XOpenDisplay(display_name);
    if (!display) {
        PyErr_Format(PyExc_SystemError, "Unable to open X11 display.");
        return NULL;
    }

    self = (X11Display_PyObject *)type->tp_alloc(type, 0);
    self->display = display;
    self->wmDeleteMessage = XInternAtom(self->display, "WM_DELETE_WINDOW", False);
    return (PyObject *)self;
}

static int
X11Display_PyObject__init(X11Display_PyObject *self, PyObject *args,
                          PyObject *kwargs)
{
    self->socket = PyInt_FromLong( ConnectionNumber(self->display) );
    return 0;
}


void
X11Display_PyObject__dealloc(X11Display_PyObject * self)
{
    printf("X11Display dealloc: %p\n", self);
    if (self->display) {
        // FIXME
        //XCloseDisplay(self->display);
    }
    Py_XDECREF(self->socket);
    self->ob_type->tp_free((PyObject*)self);
}

PyObject *
X11Display_PyObject__handle_events(X11Display_PyObject * self, PyObject * args)
{
    PyObject *events = PyList_New(0), *o;
    XEvent ev;

    XLockDisplay(self->display);
    XSync(self->display, False);
    while (XPending(self->display)) {
        XNextEvent(self->display, &ev);
        //printf("EVENT: %d\n", ev.type);
        if (ev.type == Expose) {
            o = Py_BuildValue("(i{s:i,s:(ii),s:(ii)})", Expose,
                              "window", ev.xexpose.window,
                              "pos", ev.xexpose.x, ev.xexpose.y,
                              "size", ev.xexpose.width, ev.xexpose.height);
            PyList_Append(events, o);
            Py_DECREF(o);
        }
        else if (ev.type == KeyPress) {
            char buf[100];
            KeySym keysym;
            static XComposeStatus stat;
            int key;

            // Peeled shamelessly from MPlayer.
            XLookupString(&ev.xkey, buf, sizeof(buf), &keysym, &stat);
            key = ((keysym & 0xff00) != 0 ? ((keysym & 0x00ff) + 256) : (keysym));

            o = Py_BuildValue("(i{s:i,s:i})", KeyPress,
                              "window", ev.xkey.window,
                              "key", key);
            PyList_Append(events, o);
            Py_DECREF(o);
        }
        else if (ev.type == MotionNotify) {
            o = Py_BuildValue("(i{s:i,s:(ii),s:(ii)})", MotionNotify,
                              "window", ev.xmotion.window,
                              "pos", ev.xmotion.x, ev.xmotion.y,
                              "root_pos", ev.xmotion.x_root, ev.xmotion.y_root);
            PyList_Append(events, o);
            Py_DECREF(o);
        }
        else if (ev.type == ConfigureNotify) {
            o = Py_BuildValue("(i{s:i,s:(ii),s:(ii)})", ConfigureNotify,
                              "window", ev.xconfigure.window,
                              "pos", ev.xconfigure.x, ev.xconfigure.y,
                              "size", ev.xconfigure.width, ev.xconfigure.height);
            PyList_Append(events, o);
            Py_DECREF(o);
        }
        else if (ev.type == ClientMessage) {
            char *msgtype = "unknown";
            if (ev.xclient.data.l[0] == self->wmDeleteMessage)
                msgtype = "delete";
            o = Py_BuildValue("(i{s:i,s:s})", ClientMessage,
                              "window", ev.xclient.window,
                              "type", msgtype);
            PyList_Append(events, o);
            Py_DECREF(o);
        }
        else if (ev.type == MapNotify) {
            o = Py_BuildValue("(i{s:i})", MapNotify,
                              "window", ev.xmap.window);
            PyList_Append(events, o);
            Py_DECREF(o);
        }
        else if (ev.type == UnmapNotify) {
            o = Py_BuildValue("(i{s:i})", UnmapNotify, "window", ev.xmap.window);
            PyList_Append(events, o);
            Py_DECREF(o);
        }
        else if (ev.type == FocusIn || ev.type == FocusOut) {
            o = Py_BuildValue("(i{s:i})", ev.xfocus.type,
                              "window", ev.xfocus.window);
            PyList_Append(events, o);
            Py_DECREF(o);
        }
    }
    XUnlockDisplay(self->display);
//    printf("END HANDL EVENTS\n");
    return events;
}

PyObject *
X11Display_PyObject__sync(X11Display_PyObject * self, PyObject * args)
{
    XLockDisplay(self->display);
    XSync(self->display, False);
    XUnlockDisplay(self->display);
    return Py_INCREF(Py_None), Py_None;
}

PyObject *
X11Display_PyObject__get_size(X11Display_PyObject * self, PyObject * args)
{
    int screen = -1, w, h;
    if (!PyArg_ParseTuple(args, "|i", &screen))
        return NULL;

    XLockDisplay(self->display);
    if (screen == -1)
        screen = XDefaultScreen(self->display);
    w = DisplayWidth(self->display, screen);
    h = DisplayHeight(self->display, screen);
    XUnlockDisplay(self->display);

    return Py_BuildValue("(ii)", w, h);
}

PyObject *
X11Display_PyObject__lock(X11Display_PyObject * self, PyObject * args)
{
    XLockDisplay(self->display);
    Py_INCREF(Py_None);
    return Py_None;
}

PyObject *
X11Display_PyObject__unlock(X11Display_PyObject * self, PyObject * args)
{
    XUnlockDisplay(self->display);
    Py_INCREF(Py_None);
    return Py_None;
}

PyObject *
X11Display_PyObject__get_string(X11Display_PyObject * self, PyObject * args)
{
    return Py_BuildValue("s", DisplayString(self->display));
}

PyObject *
X11Display_PyObject__glx_supported(X11Display_PyObject * self, PyObject * args)
{
#ifdef ENABLE_ENGINE_GL_X11
    static int attribs[] = { GLX_RGBA, None };
    if (glXChooseVisual(self->display, XDefaultScreen(self->display), attribs)) {
        Py_INCREF(Py_True);
        return Py_True;
    }
#endif
    Py_INCREF(Py_False);
    return Py_False;
}

PyObject *
X11Display_PyObject__composite_supported(X11Display_PyObject * self, PyObject * args)
{
#ifdef HAVE_X11_COMPOSITE
    int event_base, error_base;
    if ( XCompositeQueryExtension( self->display, &event_base, &error_base ) ) {
    // If we get here the server supports the extension
	int major = 0, minor = 2; // The highest version we support

	XCompositeQueryVersion( self->display, &major, &minor );

	// major and minor will now contain the highest version the server supports.
	// The protocol specifies that the returned version will never be higher
	// then the one requested. Version 0.2 is the first version to have the
	// XCompositeNameWindowPixmap() request.
	if ( major > 0 || minor >= 2 ) {
	    Py_INCREF(Py_True);
	    return Py_True;
	}
    }
#endif    
    Py_INCREF(Py_False);
    return Py_False;
}

PyObject *
X11Display_PyObject__composite_redirect(X11Display_PyObject * self, PyObject * args)
{
#ifdef HAVE_X11_COMPOSITE
    int wid = 0;
    if (!PyArg_ParseTuple(args, "i", &wid))
        return NULL;
    XCompositeRedirectWindow( self->display, wid, CompositeRedirectManual);
    return Py_INCREF(Py_None), Py_None;
#else
    PyErr_Format(PyExc_SystemError, "Composite extention not supported");
    return NULL;
#endif
}

PyObject *
X11Display_PyObject__get_root_id(X11Display_PyObject * self, PyObject * args)
{
    return Py_BuildValue("k", DefaultRootWindow(self->display));
}

PyMethodDef X11Display_PyObject_methods[] = {
    { "handle_events", ( PyCFunction ) X11Display_PyObject__handle_events, METH_VARARGS },
    { "sync", ( PyCFunction ) X11Display_PyObject__sync, METH_VARARGS },
    { "lock", ( PyCFunction ) X11Display_PyObject__lock, METH_VARARGS },
    { "unlock", ( PyCFunction ) X11Display_PyObject__unlock, METH_VARARGS },
    { "get_size", ( PyCFunction ) X11Display_PyObject__get_size, METH_VARARGS },
    { "get_string", ( PyCFunction ) X11Display_PyObject__get_string, METH_VARARGS },
    { "glx_supported", ( PyCFunction ) X11Display_PyObject__glx_supported, METH_VARARGS },
    { "composite_supported", ( PyCFunction ) X11Display_PyObject__composite_supported, METH_VARARGS },
    { "composite_redirect", ( PyCFunction ) X11Display_PyObject__composite_redirect, METH_VARARGS },
    { "get_root_id", ( PyCFunction ) X11Display_PyObject__get_root_id, METH_VARARGS },
    { NULL, NULL }
};


static PyMemberDef X11Display_PyObject_members[] = {
    {"socket", T_OBJECT_EX, offsetof(X11Display_PyObject, socket), 0, ""},
    {NULL}  /* Sentinel */
};


PyTypeObject X11Display_PyObject_Type = {
    PyObject_HEAD_INIT(NULL)
    0,                         /*ob_size*/
    "X11Display",              /*tp_name*/
    sizeof(X11Display_PyObject),  /*tp_basicsize*/
    0,                         /*tp_itemsize*/
    (destructor)X11Display_PyObject__dealloc, /* tp_dealloc */
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
    Py_TPFLAGS_DEFAULT | Py_TPFLAGS_BASETYPE, /*tp_flags*/
    "X11 Display Object",      /* tp_doc */
    0,   /* tp_traverse */
    0,           /* tp_clear */
    0,                     /* tp_richcompare */
    0,                     /* tp_weaklistoffset */
    0,                     /* tp_iter */
    0,                     /* tp_iternext */
    X11Display_PyObject_methods,             /* tp_methods */
    X11Display_PyObject_members,             /* tp_members */
    0,                         /* tp_getset */
    0,                         /* tp_base */
    0,                         /* tp_dict */
    0,                         /* tp_descr_get */
    0,                         /* tp_descr_set */
    0,                         /* tp_dictoffset */
    (initproc)X11Display_PyObject__init,      /* tp_init */
    0,                         /* tp_alloc */
    X11Display_PyObject__new,   /* tp_new */
};
