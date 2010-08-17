/*
 * ----------------------------------------------------------------------------
 * x11display.h
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

#ifndef _X11DISPLAY_H_
#define _X11DISPLAY_H_
#include <X11/Xlib.h>
#include <glib.h>

typedef struct {
    PyObject_HEAD

    Display *display;
    PyObject *socket,
             *x11_error_class,
             *error_callback;
    Atom wmDeleteMessage;
    int (*old_handler)(Display *, XErrorEvent *);
} X11Display_PyObject;

typedef struct {
    Display *display;
    int (*old_handler)(Display *, XErrorEvent *);
    XErrorEvent error;
} X11ErrorTrap;

extern PyTypeObject X11Display_PyObject_Type;
extern GSList *x_error_traps;
extern GHashTable *x11display_pyobjects;
int x_error_handler(Display *, XErrorEvent *);
void x_error_trap_push(void);
int x_error_trap_pop(int do_raise);

#endif
