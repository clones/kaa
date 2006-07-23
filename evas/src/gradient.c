#include <Python.h>
#include <Evas.h>

#include "object.h"
#include "gradient.h"

PyObject *
Evas_Object_PyObject_gradient_color_add(Evas_Object_PyObject * self, PyObject * args)
{
    int r, g, b, a, distance;

    if (!PyArg_ParseTuple(args, "iiiii", &r, &g, &b, &a, &distance))
        return NULL;

    BENCH_START
    evas_object_gradient_color_add(self->object, r, g, b, a, distance);
    BENCH_END
    return Py_INCREF(Py_None), Py_None;

}

PyObject *
Evas_Object_PyObject_gradient_colors_clear(Evas_Object_PyObject * self, PyObject * args)
{
    BENCH_START
    evas_object_gradient_colors_clear(self->object);
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

