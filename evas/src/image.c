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

PyObject *
Evas_Object_PyObject_image_pixels_import(Evas_Object_PyObject * self,
                                  PyObject * args)
{
    Evas_Pixel_Import_Source ps;
    PyObject *buffer;
    void *data, *p;
    int i, stride, len;


    if (!PyArg_ParseTuple(args, "Oiii", &buffer, &ps.w, &ps.h, &ps.format))
        return NULL;

    if (PyNumber_Check(buffer)) {
        data = (void *) PyLong_AsLong(buffer);
    } else {
        if (PyObject_AsReadBuffer(buffer, (const void **) &data, &len) == -1)
            return NULL;
    }
    if (ps.format == EVAS_PIXEL_FORMAT_YUV420P_601) {
        ps.rows = malloc(ps.h * 2 * sizeof(void *));
        for (i = 0, stride = ps.w, p = data; i < ps.h * 2; i++, p += stride) {
            ps.rows[i] = p;
            if (i == ps.h)
                stride >>= 1;
        }
    } else
        return PyErr_SetString(PyExc_ValueError, "Invalid pixel format"),
            (PyObject *) NULL;
    evas_object_image_pixels_import(self->object, &ps);
    free(ps.rows);
    return Py_INCREF(Py_None), Py_None;
}
