#include <Python.h>
#include <Evas.h>

#include "object.h"
#include "line.h"

PyObject *
Evas_Object_PyObject_line_xy_set(Evas_Object_PyObject * self, PyObject * args)
{
    int x1, y1, x2, y2;

    if (!PyArg_ParseTuple(args, "iiii", &x1, &y1, &x2, &y2))
        return NULL;

    BENCH_START
    evas_object_line_xy_set(self->object, x1, y1, x2, y2);
    BENCH_END
    return Py_INCREF(Py_None), Py_None;

}

PyObject *
Evas_Object_PyObject_line_xy_get(Evas_Object_PyObject * self, PyObject * args)
{
    int x1, y1, x2, y2;
    BENCH_START
    evas_object_line_xy_get(self->object, &x1, &y1, &x2, &y2);
    BENCH_END
    return Py_BuildValue("(iiii)", x1, y1, x2, y2);
}

