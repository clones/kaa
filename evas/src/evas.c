/*
 * ----------------------------------------------------------------------------
 * evas.c - main evas wrapper
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

#include "evas.h"
#include "structmember.h"
#include "object.h"
#include "textblock.h"

#include "engine_buffer.h"
#include <Evas_Engine_Buffer.h>

#include <sys/time.h>

unsigned long long __benchmark_time = 0;
unsigned long long __benchmark_start, __benchmark_end;


PyObject *evas_error;

// Exported _C_API function
Evas *evas_object_from_pyobject(Evas_PyObject *pyevas)
{
        return pyevas->evas;
}

int
check_evas(Evas *evas)
{
    if (!evas_output_method_get(evas)) {
        PyErr_Format(evas_error, "No output method set.");
        return 0;
    }

    return 1;
}


static int
Evas_PyObject__clear(Evas_PyObject *self)
{
    //printf("Evas CLEAR\n");
    if (self->dict) {
        PyObject *tmp = self->dict;
        self->dict = 0;
        PyDict_Clear(tmp);
        Py_XDECREF(tmp);
    }
    return 0;
}

static int
Evas_PyObject__traverse(Evas_PyObject *self, visitproc visit, void *arg)
{
    //printf("Evas traverse\n");
    if (self->dict) {
        int ret = visit(self->dict, arg);
        if (ret != 0)
            return ret;

    }
    if (self->dependencies) {
        int ret = visit(self->dependencies, arg);
        if (ret != 0)
            return ret;
    }
    return 0;
}

PyObject *
Evas_PyObject__new(PyTypeObject *type, PyObject * args, PyObject * kwargs)
{
    Evas_PyObject *self;

    self = (Evas_PyObject *)type->tp_alloc(type, 0);
    return (PyObject *)self;
}

static int
Evas_PyObject__init(Evas_PyObject *self, PyObject *args, PyObject *kwds)
{
    Evas *evas;
    evas = evas_new();
    if (!evas) {
        PyErr_SetString(PyExc_RuntimeError, "Unknown error creating Evas canvas");
        return -1;
    }
    self->evas = evas;
    self->dict = PyDict_New();
    self->dependencies = PyList_New(0);
    return 0;
}

static PyMemberDef Evas_PyObject_members[] = {
    {"__dict__", T_OBJECT_EX, offsetof(Evas_PyObject, dict), 0, "Attribute dictionary"},
    {"dependencies", T_OBJECT_EX, offsetof(Evas_PyObject, dependencies), 0, "Dependencies"},
    {NULL}
};


void
Evas_PyObject__dealloc(Evas_PyObject * self)
{
    printf("Evas dealloc\n");
    if (self->evas) {
        evas_free(self->evas);
    }
    Evas_PyObject__clear(self);
    Py_DECREF(self->dependencies);
    self->ob_type->tp_free((PyObject*)self);
}

PyObject *
Evas_PyObject_output_size_set(Evas_PyObject * self, PyObject * args)
{
    int w, h;

    if (!PyArg_ParseTuple(args, "(ii)", &w, &h))
        return NULL;
    BENCH_START
    evas_output_size_set(self->evas, w, h);
    BENCH_END
    return Py_INCREF(Py_None), Py_None;
}

PyObject *
Evas_PyObject_output_size_get(Evas_PyObject * self, PyObject * args)
{
    int w, h;

    BENCH_START
    evas_output_size_get(self->evas, &w, &h);
    BENCH_END
    return Py_BuildValue("(ii)", w, h);
}

PyObject *
Evas_PyObject_viewport_set(Evas_PyObject * self, PyObject * args)
{
    Evas_Coord x, y, w, h;

    if (!PyArg_ParseTuple(args, "(ii)(ii)", &x, &y, &w, &h))
        return NULL;
    BENCH_START
    evas_output_viewport_set(self->evas, x, y, w, h);
    BENCH_END
    return Py_INCREF(Py_None), Py_None;
}

PyObject *
Evas_PyObject_viewport_get(Evas_PyObject * self, PyObject * args)
{
    Evas_Coord x, y, w, h;

    BENCH_START
    evas_output_viewport_get(self->evas, &x, &y, &w, &h);
    BENCH_END
    return Py_BuildValue("((ii)(ii))", x, y, w, h);
}

PyObject *
Evas_PyObject_render(Evas_PyObject * self, PyObject * args)
{
    Evas_List *updates, *p;
    PyObject *list = PyList_New(0);

    Py_BEGIN_ALLOW_THREADS
    BENCH_START
    updates = evas_render_updates(self->evas);
    BENCH_END
    Py_END_ALLOW_THREADS
    for (p = updates; p; p = p->next) {
        Evas_Rectangle *r = p->data;
        PyObject *region = Py_BuildValue("(iiii)", r->x, r->y, r->w, r->h);
        PyList_Append(list, region);
        Py_DECREF(region);
    }
    evas_render_updates_free(updates);
    return list;
}

PyObject *
Evas_PyObject_new(PyObject * self, PyObject * args, PyObject * kwargs)
{
    Evas_PyObject *o;
    Evas *evas;

    evas = evas_new();
    if (!evas) {
        PyErr_SetString(PyExc_RuntimeError, "Unknown error creating Evas canvas");
        return NULL;
    }
    o = PyObject_NEW(Evas_PyObject, &Evas_PyObject_Type);
    o->evas = evas;
    o->dict = PyDict_New();
    return (PyObject *)o;
}
           
PyObject *
Evas_PyObject_output_set(Evas_PyObject * self, PyObject * args, PyObject * kwargs)
{
    char *render_method;

    if (!PyArg_ParseTuple(args, "s", &render_method))
        return NULL;

    if (evas_output_method_get(self->evas)) {
        PyErr_Format(evas_error, "Output method already set for this canvas.");
        return NULL;
    }

    if (!strcmp(render_method, "buffer")) {
        return engine_buffer_setup(self, kwargs);
    } else {
        PyErr_Format(evas_error, "Unsupported output method '%s'.", render_method);
        return NULL;
    }

    Py_INCREF(Py_None);
    return Py_None;
}

PyObject *
Evas_PyObject_image_cache_flush(Evas_PyObject * self, PyObject * args)
{
    BENCH_START
    evas_image_cache_flush(self->evas);
    BENCH_END
    return Py_INCREF(Py_None), Py_None;
}

PyObject *
Evas_PyObject_image_cache_reload(Evas_PyObject * self, PyObject * args)
{
    BENCH_START
    evas_image_cache_reload(self->evas);
    BENCH_END
    return Py_INCREF(Py_None), Py_None;
}

PyObject *
Evas_PyObject_image_cache_set(Evas_PyObject * self, PyObject * args)
{
    int size;

    if (!PyArg_ParseTuple(args, "i", &size))
        return NULL;
    BENCH_START
    evas_image_cache_set(self->evas, size);
    BENCH_END
    return Py_INCREF(Py_None), Py_None;
}

PyObject *
Evas_PyObject_image_cache_get(Evas_PyObject * self, PyObject * args)
{
    int cache;
    BENCH_START
    cache = evas_image_cache_get(self->evas);
    BENCH_END
    return Py_BuildValue("i", cache);
}

PyObject *
Evas_PyObject_object_rectangle_add(Evas_PyObject * self, PyObject * args)
{
    Evas_Object *o;
    BENCH_START
    o = evas_object_rectangle_add(self->evas);
    BENCH_END
    return (PyObject *)wrap_evas_object(o, self);
}

PyObject *
Evas_PyObject_object_gradient_add(Evas_PyObject * self, PyObject * args)
{
    Evas_Object *o;
    BENCH_START
    o = evas_object_gradient_add(self->evas);
    BENCH_END
    return (PyObject *)wrap_evas_object(o, self);
}

PyObject *
Evas_PyObject_object_image_add(Evas_PyObject * self, PyObject * args)
{
    Evas_Object *o;
    if (!check_evas(self->evas))
        return NULL;

    BENCH_START
    o = evas_object_image_add(self->evas);
    BENCH_END
    return (PyObject *)wrap_evas_object(o, self);
}

PyObject *
Evas_PyObject_object_text_add(Evas_PyObject * self, PyObject * args)
{
    Evas_Object *o;
    BENCH_START
    o = evas_object_text_add(self->evas);
    BENCH_END
    return (PyObject *)wrap_evas_object(o, self);
}

PyObject *
Evas_PyObject_object_textblock_add(Evas_PyObject * self, PyObject * args)
{
    Evas_Object *o;
    BENCH_START
    o = evas_object_textblock_add(self->evas);
    BENCH_END
    return (PyObject *)wrap_evas_object(o, self);
}

PyObject *
Evas_PyObject_object_name_find(Evas_PyObject * self, PyObject * args)
{
    char *name;
    Evas_Object *obj;
    if (!PyArg_ParseTuple(args, "s", &name))
        return NULL;

    BENCH_START
    obj = evas_object_name_find(self->evas, name);
    BENCH_END
    if (obj)
        return (PyObject *) wrap_evas_object(obj, self);
    Py_INCREF(Py_None);
    return Py_None;
}


PyObject *
Evas_PyObject_font_path_set(Evas_PyObject * self, PyObject * args)
{
    PyObject *list;
    int i;

    if (!PyArg_ParseTuple(args, "O!", &PyList_Type, &list))
        return NULL;

    BENCH_START
    evas_font_path_clear(self->evas);
    for (i = 0; i < PyList_Size(list); i++) {
        // printf("FONT PATH %d: %s\n", i,
        // PyString_AsString(PyList_GetItem(list, i)));
        evas_font_path_append(self->evas,
                              PyString_AsString(PyList_GetItem(list, i)));
    }
    BENCH_END
    Py_INCREF(Py_None);
    return Py_None;
}

PyObject *
Evas_PyObject_damage_rectangle_add(Evas_PyObject * self, PyObject * args)
{
    int x, y, w, h;

    if (!PyArg_ParseTuple(args, "iiii", &x, &y, &w, &h))
        return NULL;

    BENCH_START
    evas_damage_rectangle_add(self->evas, x, y, w, h);
    BENCH_END
    Py_INCREF(Py_None);
    return Py_None;
}

// *INDENT-OFF*
PyMethodDef Evas_PyObject_methods[] = {
    {"object_name_find", (PyCFunction) Evas_PyObject_object_name_find, METH_VARARGS},
    {"output_set", (PyCFunction) Evas_PyObject_output_set, METH_VARARGS | METH_KEYWORDS},
    {"font_path_set", (PyCFunction) Evas_PyObject_font_path_set, METH_VARARGS},
    {"damage_rectangle_add", (PyCFunction) Evas_PyObject_damage_rectangle_add, METH_VARARGS},

    {"output_size_set", (PyCFunction) Evas_PyObject_output_size_set, METH_VARARGS},
    {"output_size_get", (PyCFunction) Evas_PyObject_output_size_get, METH_VARARGS},
    {"viewport_set", (PyCFunction) Evas_PyObject_viewport_set, METH_VARARGS},
    {"viewport_get", (PyCFunction) Evas_PyObject_viewport_get, METH_VARARGS},
    {"render", (PyCFunction) Evas_PyObject_render, METH_VARARGS},

    {"image_cache_flush", (PyCFunction) Evas_PyObject_image_cache_flush, METH_VARARGS},
    {"image_cache_reload", (PyCFunction) Evas_PyObject_image_cache_reload, METH_VARARGS},
    {"image_cache_set", (PyCFunction) Evas_PyObject_image_cache_set, METH_VARARGS},
    {"image_cache_get", (PyCFunction) Evas_PyObject_image_cache_get, METH_VARARGS},

    {"object_rectangle_add", (PyCFunction) Evas_PyObject_object_rectangle_add, METH_VARARGS},
    {"object_image_add", (PyCFunction) Evas_PyObject_object_image_add, METH_VARARGS},
    {"object_text_add", (PyCFunction) Evas_PyObject_object_text_add, METH_VARARGS},
    {"object_textblock_add", (PyCFunction) Evas_PyObject_object_textblock_add, METH_VARARGS},
    {"object_gradient_add", (PyCFunction) Evas_PyObject_object_gradient_add, METH_VARARGS},
/* TODO:
    top_at_xy_get
    top_at_pointer_get
    top_in_rectangle_get
    evas_objects*
*/
    {NULL, NULL}
};

int
Evas_PyObject__compare(Evas_PyObject *a, Evas_PyObject *b)
{
    return (a->evas == b->evas) ? 0 : 1;
}


PyTypeObject Evas_PyObject_Type = {
    PyObject_HEAD_INIT(NULL) 
    0,                          /* ob_size */
    "_evas.Evas",               /* tp_name */
    sizeof(Evas_PyObject),      /* tp_basicsize */
    0,                          /* tp_itemsize */
    (destructor) Evas_PyObject__dealloc,        /* tp_dealloc */
    0,                          /* tp_print */
    0,                          /* tp_getattr */
    0,                          /* tp_setattr */
    (cmpfunc) Evas_PyObject__compare, /* tp_compare */
    0,                          /* tp_repr */
    0,                          /* tp_as_number */
    0,                          /* tp_as_sequence */
    0,                          /* tp_as_mapping */
    0,                          /* tp_hash */
    0,                          /* tp_call */
    0,                          /* tp_str */
    PyObject_GenericGetAttr,    /* tp_getattro */
    PyObject_GenericSetAttr,    /* tp_setattro */
    0,                          /* tp_as_buffer */
    Py_TPFLAGS_DEFAULT | Py_TPFLAGS_BASETYPE | Py_TPFLAGS_HAVE_GC, /* tp_flags */
    "Evas Canvas",               /* tp_doc */
    (traverseproc)Evas_PyObject__traverse,   /* tp_traverse */
    (inquiry)Evas_PyObject__clear,           /* tp_clear */
    0,                         /* tp_richcompare */
    0,                         /* tp_weaklistoffset */
    0,                         /* tp_iter */
    0,                         /* tp_iternext */
    Evas_PyObject_methods,     /* tp_methods */
    Evas_PyObject_members,     /* tp_members */
    0,                         /* tp_getset */
    0,                         /* tp_base */
    0,                         /* tp_dict */
    0,                         /* tp_descr_get */
    0,                         /* tp_descr_set */
    0,                         /* tp_dictoffset */
    (initproc)Evas_PyObject__init, /* tp_init */
    0,                         /* tp_alloc */
    Evas_PyObject__new,        /* tp_new */
};

PyObject *
render_method_list(PyObject *module, PyObject *args)
{
    PyObject *pylist;
    Evas_List *list, *p;
    
    pylist = PyList_New(0);

    list = evas_render_method_list();
    for (p = list; p; p = p->next)
        PyList_Append(pylist, PyString_FromString((char *)p->data));
    evas_render_method_list_free(list);
    return pylist;
}

PyObject *
evas_benchmark_reset(PyObject *module, PyObject *args)
{
    __benchmark_time = 0;
    Py_INCREF(Py_None);
    return Py_None;
}

PyObject *
evas_benchmark_get(PyObject *module, PyObject *args)
{
    return Py_BuildValue("K", __benchmark_time);
}

PyObject *
evas_benchmark_calibrate(PyObject *module, PyObject *args)
{
#ifdef BENCHMARK
    int sleep_usecs;
    unsigned long long t0, t1, tvdiff;
    struct timeval tv0, tv1;

    if (!PyArg_ParseTuple(args, "i", &sleep_usecs))
        return NULL;
    rdtscll(t0);
    gettimeofday(&tv0, NULL);
    usleep(sleep_usecs);
    rdtscll(t1);
    gettimeofday(&tv1, NULL);
    tvdiff = ((tv1.tv_sec - tv0.tv_sec) * 1000000) + (tv1.tv_usec - tv0.tv_usec);
    return Py_BuildValue("d", (double)(t1-t0)/(double)tvdiff);
#else
    return Py_BuildValue("d", 0.0);
#endif

}

PyMethodDef evas_methods[] = {
    {"render_method_list", (PyCFunction) render_method_list, METH_VARARGS},
    {"benchmark_reset", (PyCFunction) evas_benchmark_reset, METH_VARARGS},
    {"benchmark_get", (PyCFunction) evas_benchmark_get, METH_VARARGS},
    {"benchmark_calibrate", (PyCFunction) evas_benchmark_calibrate, METH_VARARGS},
    {NULL}
};

void
init_evas(void)
{
    PyObject *m, *c_api;
    static void *api_ptrs[2];

    evas_init();

    m = Py_InitModule("_evas", evas_methods);
    evas_error = PyErr_NewException("evas.EvasError", NULL, NULL);
    Py_INCREF(evas_error);
    PyModule_AddObject(m, "EvasError", evas_error);

    if (PyType_Ready(&Evas_PyObject_Type) < 0)
        return;
    Py_INCREF(&Evas_PyObject_Type);
    PyModule_AddObject(m, "Evas", (PyObject *)&Evas_PyObject_Type);

    if (PyType_Ready(&Evas_Object_PyObject_Type) < 0)
        return;
    Py_INCREF(&Evas_Object_PyObject_Type);
    PyModule_AddObject(m, "Object", (PyObject *)&Evas_Object_PyObject_Type);

    if (PyType_Ready(&Evas_Textblock_Cursor_PyObject_Type) < 0)
        return;
    Py_INCREF(&Evas_Textblock_Cursor_PyObject_Type);
    PyModule_AddObject(m, "TextBlockCursor", (PyObject *)&Evas_Textblock_Cursor_PyObject_Type);

    // Export a simple API for other extension modules to be able to access
    // and manipulate Evas objects.
    api_ptrs[0] = (void *)evas_object_from_pyobject;
    api_ptrs[1] = (void *)&Evas_PyObject_Type;
    c_api = PyCObject_FromVoidPtr((void *)api_ptrs, NULL);
    PyModule_AddObject(m, "_C_API", c_api);

    PyEval_InitThreads();
}

// vim: ts=4
