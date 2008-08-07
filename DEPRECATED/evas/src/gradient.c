/*
 * ----------------------------------------------------------------------------
 * gradient.c - evas gradient object wrapper
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

#include <Python.h>
#include <Evas.h>

#include "object.h"
#include "gradient.h"

PyObject *
Evas_Object_PyObject_gradient_color_stop_add(Evas_Object_PyObject * self, PyObject * args)
{
    int r, g, b, a, delta;

    if (!PyArg_ParseTuple(args, "iiiii", &r, &g, &b, &a, &delta))
        return NULL;

    BENCH_START
#if EVAS_VERSION >= 2363940
    evas_object_gradient_color_stop_add(self->object, r, g, b, a, delta);
#else
    evas_object_gradient_color_add(self->object, r, g, b, a, delta);
#endif
    BENCH_END
    return Py_INCREF(Py_None), Py_None;

}

PyObject *
Evas_Object_PyObject_gradient_clear(Evas_Object_PyObject * self, PyObject * args)
{
    BENCH_START
#if EVAS_VERSION >= 2363940
    evas_object_gradient_clear(self->object);
#else
    evas_object_gradient_colors_clear(self->object);
#endif
    BENCH_END
    return Py_INCREF(Py_None), Py_None;
}


PyObject *
Evas_Object_PyObject_gradient_angle_set(Evas_Object_PyObject * self, PyObject * args)
{
    int angle;
    if (!PyArg_ParseTuple(args, "i", &angle))
        return NULL;

    BENCH_START
    evas_object_gradient_angle_set(self->object, angle);
    BENCH_END
    return Py_INCREF(Py_None), Py_None;

}

PyObject *
Evas_Object_PyObject_gradient_angle_get(Evas_Object_PyObject * self, PyObject * args)
{
    int angle;
    BENCH_START
    angle = evas_object_gradient_angle_get(self->object);
    BENCH_END
    return Py_BuildValue("i", angle);
}

