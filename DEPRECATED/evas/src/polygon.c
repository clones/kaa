#include <Python.h>
#include <Evas.h>

#include "object.h"
#include "polygon.h"

PyObject *
Evas_Object_PyObject_polygon_point_add(Evas_Object_PyObject * self, PyObject * args)
{
    int x, y;

    if (!PyArg_ParseTuple(args, "ii", &x, &y))
        return NULL;

    BENCH_START
    evas_object_polygon_point_add(self->object, x, y);
    BENCH_END
    return Py_INCREF(Py_None), Py_None;

}

PyObject *
Evas_Object_PyObject_polygon_points_clear(Evas_Object_PyObject * self, PyObject * args)
{
    BENCH_START
    evas_object_polygon_points_clear(self->object);
    BENCH_END
    return Py_INCREF(Py_None), Py_None;
}

