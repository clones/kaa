/*
 * ----------------------------------------------------------------------------
 * evas.h
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
