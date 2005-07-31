#include <Python.h>
#include <Evas.h>

#include "object.h"
#include "image.h"

PyObject *
Evas_Object_PyObject_image_file_set(Evas_Object_PyObject * self, PyObject * args)
{
    char *filename;

    if (!PyArg_ParseTuple(args, "s", &filename))
        return NULL;

    evas_object_image_file_set(self->object, filename, NULL);
    return Py_INCREF(Py_None), Py_None;

}

PyObject *
Evas_Object_PyObject_image_file_get(Evas_Object_PyObject * self, PyObject * args)
{
    char *filename;

    evas_object_image_file_get(self->object, &filename, NULL);
    return Py_BuildValue("s", filename);
}

/****************************************************************************/

PyObject *
Evas_Object_PyObject_image_fill_set(Evas_Object_PyObject * self, PyObject * args)
{
    Evas_Coord x, y, w, h;

    if (!PyArg_ParseTuple(args, "(ii)(ii)", &x, &y, &w, &h))
        return NULL;

    evas_object_image_fill_set(self->object, x, y, w, h);
    return Py_INCREF(Py_None), Py_None;
}

PyObject *
Evas_Object_PyObject_image_fill_get(Evas_Object_PyObject * self, PyObject * args)
{
    Evas_Coord x, y, w, h;

    evas_object_image_fill_get(self->object, &x, &y, &w, &h);
    return Py_BuildValue("((ii)(ii))", x, y, w, h);
}

/****************************************************************************/

PyObject *
Evas_Object_PyObject_image_size_set(Evas_Object_PyObject * self, PyObject * args)
{
    int w, h;

    if (!PyArg_ParseTuple(args, "(ii)", &w, &h))
        return NULL;

    evas_object_image_size_set(self->object, w, h);
    return Py_INCREF(Py_None), Py_None;
}

PyObject *
Evas_Object_PyObject_image_size_get(Evas_Object_PyObject * self, PyObject * args)
{
    int w, h;

    evas_object_image_size_get(self->object, &w, &h);
    return Py_BuildValue("(ii)", w, h);
}

/****************************************************************************/

PyObject *
Evas_Object_PyObject_image_alpha_get(Evas_Object_PyObject * self, PyObject * args)
{
    if (evas_object_image_alpha_get(self->object))
        return Py_INCREF(Py_True), Py_True;
    return Py_INCREF(Py_False), Py_False;
}

PyObject *
Evas_Object_PyObject_image_alpha_set(Evas_Object_PyObject * self, PyObject * args)
{
    int has_alpha;

    if (!PyArg_ParseTuple(args, "i", &has_alpha))
        return NULL;

    evas_object_image_alpha_set(self->object, has_alpha);
    return Py_INCREF(Py_None), Py_None;
}

/****************************************************************************/

PyObject *
Evas_Object_PyObject_image_smooth_scale_get(Evas_Object_PyObject * self,
                                     PyObject * args)
{
    if (evas_object_image_smooth_scale_get(self->object))
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

    evas_object_image_smooth_scale_set(self->object, smooth_scale);
    return Py_INCREF(Py_None), Py_None;
}

/****************************************************************************/

PyObject *
Evas_Object_PyObject_image_load_error_get(Evas_Object_PyObject * self,
                                   PyObject * args)
{
    int err = evas_object_image_load_error_get(self->object);

    return Py_BuildValue("i", err);
}


PyObject *
Evas_Object_PyObject_image_reload(Evas_Object_PyObject * self, PyObject * args)
{
    evas_object_image_reload(self->object);
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
        is_write_buffer = 1;
        data = (void *) PyLong_AsLong(buffer);
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

    // printf("DATA SET buf=%x is_write_buffer=%d copy=%d\n", data,
    // is_write_buffer, copy);
    if (copy == 0 || is_write_buffer)
        evas_object_image_data_set(self->object, data);
    else if (copy == 1 || !is_write_buffer)
        evas_object_image_data_copy_set(self->object, data);
    return Py_INCREF(Py_None), Py_None;
}


PyObject *
Evas_Object_PyObject_image_data_get(Evas_Object_PyObject * self, PyObject * args)
{
    unsigned char *data;
    int for_writing = 1, w, h;

    if (!PyArg_ParseTuple(args, "|i", &for_writing))
        return NULL;

    data = evas_object_image_data_get(self->object, 0);
    evas_object_image_size_get(self->object, &w, &h);
    // FIXME: implement buffer interace for Evas Object pyobject.
    if (for_writing)
        return PyBuffer_FromReadWriteMemory(data, w * h * 4);
    else
        return PyBuffer_FromMemory(data, w * h * 4);
}

/****************************************************************************/

PyObject *
Evas_Object_PyObject_image_pixels_dirty_set(Evas_Object_PyObject * self,
                                     PyObject * args)
{
    int dirty;

    if (!PyArg_ParseTuple(args, "i", &dirty))
        return NULL;

    evas_object_image_pixels_dirty_set(self->object, dirty);
    return Py_INCREF(Py_None), Py_None;
}


PyObject *
Evas_Object_PyObject_image_pixels_dirty_get(Evas_Object_PyObject * self,
                                     PyObject * args)
{
    if (evas_object_image_pixels_dirty_get(self->object))
        return Py_INCREF(Py_True), Py_True;
    return Py_INCREF(Py_False), Py_False;
}

static void *
_get_ptr_from_pyobject(PyObject *o)
{
    void *data;
    int len;

    if (PyNumber_Check(o)) {
        data = (void *) PyLong_AsLong(o);
    } else {
        if (PyObject_AsReadBuffer(o, (const void **) &data, &len) == -1)
            return NULL;
    }
    return data;
}


PyObject *
Evas_Object_PyObject_image_pixels_import(Evas_Object_PyObject * self,
                                  PyObject * args)
{
    Evas_Pixel_Import_Source ps;
    PyObject *data;
    void *p, *planes[3] = {0,0,0};
    int i, stride, len, plane;

    if (!PyArg_ParseTuple(args, "Oiii", &data, &ps.w, &ps.h, &ps.format))
        return NULL;

    /* Data can be a single buffer/int pointing to memory that holds each
       plane contiguously, or a tuple of buffer/ints pointing to each
       individual plane. */
    if (!PyTuple_Check(data)) {
        if ((planes[0] = _get_ptr_from_pyobject(data)) == 0)
            return NULL;
        planes[1] = planes[0] + (ps.w * ps.h);
        planes[2] = planes[1] + ((ps.w * ps.h) >> 2);
        printf("Planes 0=%x 1=%x 2=%x\n", planes[0], planes[1], planes[2]);
    } else {
        if (PySequence_Length(data) != 3) {
            PyErr_Format(PyExc_ValueError, "Invalid size for planes tuple");
            return NULL;
        }
        for (i = 0; i < 3; i++) {
            PyObject *o = PyTuple_GetItem(data, i);
            if ((planes[i] = _get_ptr_from_pyobject(o)) == 0)
                return NULL;
        }
    }

    if (ps.format == EVAS_PIXEL_FORMAT_YUV420P_601) {
        ps.rows = malloc(ps.h * 2 * sizeof(void *));
        stride = ps.w;
        for (i = 0, plane = 0, p = planes[0]; i < ps.h * 2; i++) {
            ps.rows[i] = p;
            if (i == ps.h)
                stride >>= 1;
            if (i == ps.h || i == ps.h+(ps.h/2)) 
                p = planes[++plane];
            else
                p += stride;
        }
    } else {
        PyErr_SetString(PyExc_ValueError, "Invalid pixel format");
        return NULL;
    }

    evas_object_image_pixels_import(self->object, &ps);
    free(ps.rows);
    return Py_INCREF(Py_None), Py_None;
}
