#include "xine.h"

// Maps xine object actresses to Xine python objects
PyObject *xine_object_to_pyobject_dict = 0;

void
xine_object_to_pyobject_register(void *ptr, PyObject *o)
{
    PyObject *key = PyLong_FromLong((long)ptr), *val;
    if (!PyMapping_HasKey(xine_object_to_pyobject_dict, key)) {
        val = PyCObject_FromVoidPtr(o, NULL);
        PyDict_SetItem(xine_object_to_pyobject_dict, key, val);
        Py_DECREF(val);
    }
    Py_DECREF(key);
}

void
xine_object_to_pyobject_unregister(void *ptr)
{
    PyObject *key = PyLong_FromLong((long)ptr);
    if (PyMapping_HasKey(xine_object_to_pyobject_dict, key)) {
        PyDict_DelItem(xine_object_to_pyobject_dict, key);
    }
    Py_DECREF(key);
}

PyObject *
xine_object_to_pyobject_find(void *ptr)
{
    PyObject *key = PyLong_FromLong((long)ptr);
    PyObject *o = NULL;
    if (PyMapping_HasKey(xine_object_to_pyobject_dict, key)) {
        o = PyDict_GetItem(xine_object_to_pyobject_dict, key);
    }
    Py_DECREF(key);
    if (o)
        return (PyObject *)PyCObject_AsVoidPtr(o);
    return NULL;
}


//
// GC helper functions
int
pyxine_gc_helper_clear(PyObject ***list)
{
    int i;
    for (i = 0; list[i]; i++) {
        if (!*list[i])
            continue;
        PyObject *tmp = *list[i];
        *list[i] = 0;
        Py_DECREF(tmp);
    }
    return 0;
}

int
pyxine_gc_helper_traverse(PyObject ***list, visitproc visit, void *arg)
{
    int i, ret;
    for (i = 0; list[i]; i++) {
        if (!*list[i])
            continue;
        ret = visit(*list[i], arg);
        if (ret != 0)
            return ret;
    }
    return 0;
}

