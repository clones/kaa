/*
 * ----------------------------------------------------------------------------
 * text.c - evas text object wrapper
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
#include "text.h"

PyObject *
Evas_Object_PyObject_text_font_set(Evas_Object_PyObject * self, PyObject * args)
{
    char *font;
    int size;

    if (!PyArg_ParseTuple(args, "si", &font, &size))
        return NULL;

    BENCH_START
    evas_object_text_font_set(self->object, font, size);
    BENCH_END
    return Py_INCREF(Py_None), Py_None;

}

PyObject *
Evas_Object_PyObject_text_font_get(Evas_Object_PyObject * self, PyObject * args)
{
    const char *font;
    int size;

    BENCH_START
    evas_object_text_font_get(self->object, &font, &size);
    BENCH_END
    return Py_BuildValue("(si)", font, size);
}

/****************************************************************************/

PyObject *
Evas_Object_PyObject_text_text_set(Evas_Object_PyObject * self, PyObject * args)
{
    char *text;

    if (!PyArg_ParseTuple(args, "s", &text))
        return NULL;

    BENCH_START
    evas_object_text_text_set(self->object, text);
    BENCH_END
    return Py_INCREF(Py_None), Py_None;

}

PyObject *
Evas_Object_PyObject_text_text_get(Evas_Object_PyObject * self, PyObject * args)
{
    const char *text;
    BENCH_START
    text = evas_object_text_text_get(self->object);
    BENCH_END
    return Py_BuildValue("s", text);
}

/****************************************************************************/

PyObject *
Evas_Object_PyObject_text_font_source_set(Evas_Object_PyObject * self,
                                   PyObject * args)
{
    char *source;

    if (!PyArg_ParseTuple(args, "s", &source))
        return NULL;

    BENCH_START
    evas_object_text_font_source_set(self->object, source);
    BENCH_END
    return Py_INCREF(Py_None), Py_None;

}

PyObject *
Evas_Object_PyObject_text_font_source_get(Evas_Object_PyObject * self,
                                   PyObject * args)
{
    const char *source;
    BENCH_START
    source = evas_object_text_font_source_get(self->object);
    BENCH_END
    return Py_BuildValue("s", source);
}

/****************************************************************************
 * METRIC FUNCTIONS
 */

#define func_template(func) \
    PyObject * \
    Evas_Object_PyObject_text_ ## func (Evas_Object_PyObject *self, PyObject *args) { \
        int val; \
        BENCH_START \
        val = evas_object_text_ ## func (self->object); \
        BENCH_END \
        return Py_BuildValue("i", val); \
    }

func_template(ascent_get);
func_template(descent_get);
func_template(max_ascent_get);
func_template(max_descent_get);
func_template(horiz_advance_get);
func_template(vert_advance_get);
func_template(inset_get);

PyObject *
Evas_Object_PyObject_text_char_pos_get(Evas_Object_PyObject * self, PyObject * args)
{
    int pos;
    Evas_Coord cx, cy, cw, ch;

    if (!PyArg_ParseTuple(args, "i", &pos))
        return NULL;

    BENCH_START
    evas_object_text_char_pos_get(self->object, pos, &cx, &cy, &cw, &ch);
    BENCH_END
    return Py_BuildValue("(iiii)", cx, cy, cw, ch);
}

PyObject *
Evas_Object_PyObject_text_char_coords_get(Evas_Object_PyObject * self,
                                   PyObject * args)
{
    int x, y;
    Evas_Coord cx, cy, cw, ch;

    if (!PyArg_ParseTuple(args, "ii", &x, &y))
        return NULL;

    BENCH_START
    evas_object_text_char_coords_get(self->object, x, y, &cx, &cy, &cw, &ch);
    BENCH_END
    return Py_BuildValue("(iiii)", cx, cy, cw, ch);
}

/****************************************************************************/

PyObject *
Evas_Object_PyObject_text_style_pad_get(Evas_Object_PyObject * self,
                                   PyObject * args)
{
    int l, r, t, b;

    BENCH_START
    evas_object_text_style_pad_get(self->object, &l, &r, &t, &b);
    BENCH_END
    return Py_BuildValue("(iiii)", l, r, t, b);
}

