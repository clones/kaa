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

    evas_object_gradient_color_add(self->object, r, g, b, a, distance);
    return Py_INCREF(Py_None), Py_None;

}

PyObject *
Evas_Object_PyObject_gradient_colors_clear(Evas_Object_PyObject * self, PyObject * args)
{
    evas_object_gradient_colors_clear(self->object);
    return Py_INCREF(Py_None), Py_None;
}


PyObject *
Evas_Object_PyObject_gradient_angle_set(Evas_Object_PyObject * self, PyObject * args)
{
    int angle;
    if (!PyArg_ParseTuple(args, "i", &angle))
        return NULL;

    evas_object_gradient_angle_set(self->object, angle);
    return Py_INCREF(Py_None), Py_None;

}

PyObject *
Evas_Object_PyObject_gradient_angle_get(Evas_Object_PyObject * self, PyObject * args)
{
    return Py_BuildValue("i", evas_object_gradient_angle_get(self->object));
}

