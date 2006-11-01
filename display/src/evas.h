/*
 * ----------------------------------------------------------------------------
 * evas.h
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
#include "display.h"

#ifndef _EVAS_H_
#define _EVAS_H_

#ifdef USE_EVAS
#include "x11window.h"
#include <Evas.h>
extern Evas *(*evas_object_from_pyobject)(PyObject *pyevas);

X11Window_PyObject *new_evas_software_x11(PyObject *, PyObject *, PyObject *);

#ifdef ENABLE_ENGINE_GL_X11
X11Window_PyObject *new_evas_gl_x11(PyObject *, PyObject *, PyObject *);
#endif

#endif // USE_EVAS
#endif // _EVAS_H_
