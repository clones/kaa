/*
 * ----------------------------------------------------------------------------
 * libcandy module init
 * ----------------------------------------------------------------------------
 * $Id$
 *
 * ----------------------------------------------------------------------------
 * kaa-candy - Third generation Canvas System using Clutter as backend
 * Copyright (C) 2006 OpenedHand / 2008-2009 Dirk Meyer, Jason Tackaberry
 *
 * First Edition: Dirk Meyer <dischi@freevo.org>
 * Maintainer:    Dirk Meyer <dischi@freevo.org>
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

#ifdef HAVE_CONFIG_H
#include "config.h"
#endif

#include <pygobject.h>
#include <clutter/clutter.h>
#include "libcandy.h"

void libcandy_register_classes (PyObject *d);
extern PyMethodDef libcandy_functions[];

DL_EXPORT (void)
initlibcandy (void)
{
        PyObject *m, *d;

        init_pygobject ();

        if (PyImport_ImportModule ("clutter") == NULL) {
                PyErr_SetString (PyExc_ImportError,
                                 "could not import clutter");
                return;
        }

        m = Py_InitModule ("libcandy", libcandy_functions);
        d = PyModule_GetDict (m);

        libcandy_register_classes (d);

        if (PyErr_Occurred ()) {
                Py_FatalError ("unable to initialise libcandy module");
        }
}
