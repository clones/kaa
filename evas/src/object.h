/*
 * ----------------------------------------------------------------------------
 * object.h - basic evas object wrapper
 * ----------------------------------------------------------------------------
 * $Id$
 *
 * ----------------------------------------------------------------------------
 * kaa.evas - An evas wrapper for Python
 * Copyright (C) 2006 Jason Tackaberry <tack@sault.org>
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

#include "evas.h"

#define Evas_Object_PyObject_Check(v) ((v)->ob_type == &Evas_Object_PyObject_Type)

typedef struct {
    PyObject_HEAD
    Evas_Object *object;

} Evas_Object_PyObject;

extern PyTypeObject Evas_Object_PyObject_Type;

Evas_Object_PyObject *wrap_evas_object(Evas_Object *, Evas_PyObject *);

