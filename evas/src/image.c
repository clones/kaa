/*
 * ----------------------------------------------------------------------------
 * image.c - image evas object wrapper
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
#include "image.h"

void *
get_ptr_from_pyobject(PyObject *o, int *len)
{
    void *data;
    int data_len;

    if (PyNumber_Check(o)) {
        data = (void *) PyLong_AsLong(o);
    } else {
        if (PyObject_AsReadBuffer(o, (const void **) &data, &data_len) == -1)
            return NULL;
        if (len)
            *len = data_len;
    }
    return data;
}

static void **
_yuv_planes_to_rows(PyObject *data, int w, int h)
{
    int i, stride, plane;
    void **rows;
    void *p, *planes[3] = {0, 0, 0};
    /* Data can be a single buffer/int pointing to memory that holds each
       plane contiguously, or a tuple of buffer/ints pointing to each
       individual plane. */
    if (!PyTuple_Check(data)) {
        if ((planes[0] = get_ptr_from_pyobject(data, NULL)) == 0)
            return NULL;
        planes[1] = planes[0] + (w * h);
        planes[2] = planes[1] + ((w * h) >> 2);
        //printf("Planes (%d,%d) 0=%u 1=%u 2=%u\n", ps.w, ps.h, planes[0], planes[1], planes[2]);
    } else {
        if (PySequence_Length(data) != 3) {
            PyErr_Format(PyExc_ValueError, "Invalid size for planes tuple");
            return NULL;
        }
        for (i = 0; i < 3; i++) {
            PyObject *o = PyTuple_GetItem(data, i);
            planes[i] = get_ptr_from_pyobject(o, NULL);
            if (planes[i] == 0 && i == 0)
                return NULL;
        }
    }
    rows = malloc(h * 2 * sizeof(void *));
    stride = w;
    for (i = 0, plane = 0, p = planes[0]; i < h * 2; i++) {
        rows[i] = p;
        if (i == h)
            stride >>= 1;
        if (i == h || i == h+(h/2)) 
            p = planes[++plane];
        else
            p += stride;
    }
    return rows;
}

PyObject *
Evas_Object_PyObject_image_file_set(Evas_Object_PyObject * self, PyObject * args)
{
    char *filename;

    if (!PyArg_ParseTuple(args, "s", &filename))
        return NULL;

    BENCH_START
    evas_object_image_file_set(self->object, filename, NULL);
    BENCH_END
    return Py_INCREF(Py_None), Py_None;

}

PyObject *
Evas_Object_PyObject_image_file_get(Evas_Object_PyObject * self, PyObject * args)
{
    const char *filename;

    BENCH_START
    evas_object_image_file_get(self->object, &filename, NULL);
    BENCH_END
    return Py_BuildValue("s", filename);
}

/****************************************************************************/

PyObject *
Evas_Object_PyObject_image_fill_set(Evas_Object_PyObject * self, PyObject * args)
{
    Evas_Coord x, y, w, h;

    if (!PyArg_ParseTuple(args, "(ii)(ii)", &x, &y, &w, &h))
        return NULL;

    BENCH_START
    evas_object_image_fill_set(self->object, x, y, w, h);
    BENCH_END
    return Py_INCREF(Py_None), Py_None;
}

PyObject *
Evas_Object_PyObject_image_fill_get(Evas_Object_PyObject * self, PyObject * args)
{
    Evas_Coord x, y, w, h;

    BENCH_START
    evas_object_image_fill_get(self->object, &x, &y, &w, &h);
    BENCH_END
    return Py_BuildValue("((ii)(ii))", x, y, w, h);
}

/****************************************************************************/

PyObject *
Evas_Object_PyObject_image_border_set(Evas_Object_PyObject * self, PyObject * args)
{
    int l, r, t, b;

    if (!PyArg_ParseTuple(args, "iiii", &l, &r, &t, &b))
        return NULL;

    BENCH_START
    evas_object_image_border_set(self->object, l, r, t, b);
    BENCH_END
    return Py_INCREF(Py_None), Py_None;
}

PyObject *
Evas_Object_PyObject_image_border_get(Evas_Object_PyObject * self, PyObject * args)
{
    int l, r, t, b;

    BENCH_START
    evas_object_image_border_get(self->object, &l, &r, &t, &b);
    BENCH_END
    return Py_BuildValue("(iiii)", l, r, t, b);
}

/****************************************************************************/

PyObject *
Evas_Object_PyObject_image_border_center_fill_set(Evas_Object_PyObject * self, PyObject * args)
{
    int fill;

    if (!PyArg_ParseTuple(args, "i", &fill))
        return NULL;

    BENCH_START
    evas_object_image_border_center_fill_set(self->object, fill);
    BENCH_END
    return Py_INCREF(Py_None), Py_None;
}

PyObject *
Evas_Object_PyObject_image_border_center_fill_get(Evas_Object_PyObject * self, PyObject * args)
{
    int result;
    BENCH_START
    result = evas_object_image_border_center_fill_get(self->object);
    BENCH_END
    if (result)
        return Py_INCREF(Py_True), Py_True;
    return Py_INCREF(Py_False), Py_False;
}
/****************************************************************************/

PyObject *
Evas_Object_PyObject_image_size_set(Evas_Object_PyObject * self, PyObject * args)
{
    int w, h;

    if (!PyArg_ParseTuple(args, "(ii)", &w, &h))
        return NULL;

    BENCH_START
    evas_object_image_size_set(self->object, w, h);
    BENCH_END
    return Py_INCREF(Py_None), Py_None;
}

PyObject *
Evas_Object_PyObject_image_size_get(Evas_Object_PyObject * self, PyObject * args)
{
    int w, h;

    BENCH_START
    evas_object_image_size_get(self->object, &w, &h);
    BENCH_END
    return Py_BuildValue("(ii)", w, h);
}

/****************************************************************************/

PyObject *
Evas_Object_PyObject_image_alpha_get(Evas_Object_PyObject * self, PyObject * args)
{
    int alpha;
    BENCH_START
    alpha = evas_object_image_alpha_get(self->object);
    BENCH_END

    if (alpha)
        return Py_INCREF(Py_True), Py_True;
    return Py_INCREF(Py_False), Py_False;
}

PyObject *
Evas_Object_PyObject_image_alpha_set(Evas_Object_PyObject * self, PyObject * args)
{
    int has_alpha;

    if (!PyArg_ParseTuple(args, "i", &has_alpha))
        return NULL;

    BENCH_START
    evas_object_image_alpha_set(self->object, has_alpha);
    BENCH_END
    return Py_INCREF(Py_None), Py_None;
}

/****************************************************************************/

PyObject *
Evas_Object_PyObject_image_smooth_scale_get(Evas_Object_PyObject * self,
                                     PyObject * args)
{
    int smooth_scale;
    BENCH_START
    smooth_scale = evas_object_image_smooth_scale_get(self->object);
    BENCH_END
    if (smooth_scale)
        return Py_INCREF(Py_True), Py_True;
    return Py_INCREF(Py_False), Py_False;
}

PyObject *
Evas_Object_PyObject_image_smooth_scale_set(Evas_Object_PyObject * self,
                                     PyObject * args)
{
    int smooth_scale;

    if (!PyArg_ParseTuple(args, "i", &smooth_scale))
        return NULL;

    BENCH_START
    evas_object_image_smooth_scale_set(self->object, smooth_scale);
    BENCH_END
    return Py_INCREF(Py_None), Py_None;
}

/****************************************************************************/

PyObject *
Evas_Object_PyObject_image_load_error_get(Evas_Object_PyObject * self,
                                   PyObject * args)
{
    int err;
    BENCH_START
    err = evas_object_image_load_error_get(self->object);
    BENCH_END

    return Py_BuildValue("i", err);
}


PyObject *
Evas_Object_PyObject_image_reload(Evas_Object_PyObject * self, PyObject * args)
{
    BENCH_START
    evas_object_image_reload(self->object);
    BENCH_END
    return Py_INCREF(Py_None), Py_None;
}

/****************************************************************************/

PyObject *
Evas_Object_PyObject_image_data_set(Evas_Object_PyObject * self, PyObject * args)
{
    PyObject *buffer;
    void *data;
    int len, result, is_write_buffer = 0, copy;

    if (!PyArg_ParseTuple(args, "Oi", &buffer, &copy))
        return NULL;

    if (PyNumber_Check(buffer)) {
        int cspace = evas_object_image_colorspace_get(self->object);
        if (cspace == EVAS_COLORSPACE_YCBCR422P601_PL || cspace == EVAS_COLORSPACE_YCBCR422P709_PL) {
            int w, h;
            evas_object_image_size_get(self->object, &w, &h);
            data = _yuv_planes_to_rows(buffer, w, h);
            is_write_buffer = 1;
        } else {
            is_write_buffer = 1;
            data = (void *) PyLong_AsLong(buffer);
        }
    } else {
        result = PyObject_AsWriteBuffer(buffer, &data, &len);
        if (result != -1) {
            is_write_buffer = 1;
        } else {
            PyErr_Clear();
            result =
                PyObject_AsReadBuffer(buffer, (const void **) &data, &len);
        }
        if (result == -1)
            return NULL;
    }

    //printf("DATA SET buf=%x is_write_buffer=%d copy=%d\n", data, is_write_buffer, copy);
    BENCH_START
    if (copy == 1 || !is_write_buffer)
        evas_object_image_data_copy_set(self->object, data);
    else
        evas_object_image_data_set(self->object, data);
    BENCH_END
    return Py_INCREF(Py_None), Py_None;
}


PyObject *
Evas_Object_PyObject_image_data_get(Evas_Object_PyObject * self, PyObject * args)
{
    unsigned char *data;
    int for_writing = 1, w, h, cspace;

    if (!PyArg_ParseTuple(args, "|i", &for_writing))
        return NULL;

    cspace = evas_object_image_colorspace_get(self->object);
    if (cspace == EVAS_COLORSPACE_YCBCR422P601_PL || cspace == EVAS_COLORSPACE_YCBCR422P709_PL) {
        // TODO
        printf("NYI\n");
        return Py_INCREF(Py_None), Py_None;
    }

    BENCH_START
    data = evas_object_image_data_get(self->object, 0);
    evas_object_image_size_get(self->object, &w, &h);
    BENCH_END
    // FIXME: implement buffer interace for Evas Object pyobject.
    if (for_writing)
        return PyBuffer_FromReadWriteMemory(data, w * h * 4);
    else
        return PyBuffer_FromMemory(data, w * h * 4);
}

PyObject *
Evas_Object_PyObject_image_data_update_add(Evas_Object_PyObject * self, PyObject * args)
{
    int x, y, w, h;

    if (!PyArg_ParseTuple(args, "iiii", &x, &y, &w, &h))
        return NULL;

    BENCH_START
    evas_object_image_data_update_add(self->object, x, y, w, h);
    BENCH_END
    return Py_INCREF(Py_None), Py_None;
}

/****************************************************************************/

PyObject *
Evas_Object_PyObject_image_pixels_dirty_set(Evas_Object_PyObject * self,
                                     PyObject * args)
{
    int dirty;

    if (!PyArg_ParseTuple(args, "i", &dirty))
        return NULL;

    BENCH_START
    evas_object_image_pixels_dirty_set(self->object, dirty);
    BENCH_END
    return Py_INCREF(Py_None), Py_None;
}


PyObject *
Evas_Object_PyObject_image_pixels_dirty_get(Evas_Object_PyObject * self,
                                     PyObject * args)
{
    int dirty;
    BENCH_START
    dirty = evas_object_image_pixels_dirty_get(self->object);
    BENCH_END
    if (dirty)
        return Py_INCREF(Py_True), Py_True;
    return Py_INCREF(Py_False), Py_False;
}

PyObject *
Evas_Object_PyObject_image_pixels_import(Evas_Object_PyObject * self,
                                  PyObject * args)
{
    Evas_Pixel_Import_Source ps;
    PyObject *data;
    int result;

    if (!PyArg_ParseTuple(args, "Oiii", &data, &ps.w, &ps.h, &ps.format))
        return NULL;


    if (ps.format == EVAS_PIXEL_FORMAT_YUV420P_601) {
        ps.rows = _yuv_planes_to_rows(data, ps.w, ps.h);
        BENCH_START
        result = evas_object_image_pixels_import(self->object, &ps);
        BENCH_END
        free(ps.rows);
    } 
    else {
        PyErr_SetString(PyExc_ValueError, "Invalid pixel format");
        return NULL;
    }

    return Py_BuildValue("i", result);
}

PyObject *
Evas_Object_PyObject_image_colorspace_set(Evas_Object_PyObject * self, PyObject * args)
{
    int colorspace;

    if (!PyArg_ParseTuple(args, "i", &colorspace))
        return NULL;

    BENCH_START
    evas_object_image_colorspace_set(self->object, (Evas_Colorspace)colorspace);
    BENCH_END
    return Py_INCREF(Py_None), Py_None;
}

PyObject *
Evas_Object_PyObject_image_colorspace_get(Evas_Object_PyObject * self, PyObject * args)
{
    int colorspace;

    BENCH_START
    colorspace = evas_object_image_colorspace_get(self->object);
    BENCH_END
    return Py_BuildValue("i", colorspace);
}
