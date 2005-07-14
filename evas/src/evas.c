#include "evas.h"
#include "structmember.h"
#include "object.h"

#include "engine_buffer.h"
#include <Evas_Engine_Buffer.h>

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
    evas_output_size_set(self->evas, w, h);
    return Py_INCREF(Py_None), Py_None;
}

PyObject *
Evas_PyObject_output_size_get(Evas_PyObject * self, PyObject * args)
{
    int w, h;

    evas_output_size_get(self->evas, &w, &h);
    return Py_BuildValue("(ii)", w, h);
}

PyObject *
Evas_PyObject_viewport_set(Evas_PyObject * self, PyObject * args)
{
    Evas_Coord x, y, w, h;

    if (!PyArg_ParseTuple(args, "(ii)(ii)", &x, &y, &w, &h))
        return NULL;
    evas_output_viewport_set(self->evas, x, y, w, h);
    return Py_INCREF(Py_None), Py_None;
}

PyObject *
Evas_PyObject_viewport_get(Evas_PyObject * self, PyObject * args)
{
    Evas_Coord x, y, w, h;

    evas_output_viewport_get(self->evas, &x, &y, &w, &h);
    return Py_BuildValue("((ii)(ii))", x, y, w, h);
}

PyObject *
Evas_PyObject_render(Evas_PyObject * self, PyObject * args)
{
    Evas_List *updates, *p;
    PyObject *list = PyList_New(0);

    updates = evas_render_updates(self->evas);
    for (p = updates; p; p = p->next) {
        Evas_Rectangle *r = p->data;
        PyList_Append(list, Py_BuildValue("(iiii)", r->x, r->y, r->w, r->h));
    }
    evas_render_updates_free(updates);
    return list;
}

PyObject *
Evas_PyObject_new(PyObject * self, PyObject * args, PyObject * kwargs)
{
    PyObject *evas_instance;
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
        if (!engine_buffer_setup(self, kwargs))
            return NULL;
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
    evas_image_cache_flush(self->evas);
    return Py_INCREF(Py_None), Py_None;
}

PyObject *
Evas_PyObject_image_cache_reload(Evas_PyObject * self, PyObject * args)
{
    evas_image_cache_reload(self->evas);
    return Py_INCREF(Py_None), Py_None;
}

PyObject *
Evas_PyObject_image_cache_set(Evas_PyObject * self, PyObject * args)
{
    int size;

    if (!PyArg_ParseTuple(args, "i", &size))
        return NULL;
    evas_image_cache_set(self->evas, size);
    return Py_INCREF(Py_None), Py_None;
}

PyObject *
Evas_PyObject_image_cache_get(Evas_PyObject * self, PyObject * args)
{
    return Py_BuildValue("i", evas_image_cache_get(self->evas));
}

PyObject *
Evas_PyObject_object_rectangle_add(Evas_PyObject * self, PyObject * args)
{
    return (PyObject *)
        wrap_evas_object(evas_object_rectangle_add(self->evas), self);
}

PyObject *
Evas_PyObject_object_image_add(Evas_PyObject * self, PyObject * args)
{
    if (!check_evas(self->evas))
        return NULL;

    return (PyObject *) wrap_evas_object(evas_object_image_add(self->evas),
                                         self);
}

PyObject *
Evas_PyObject_object_text_add(Evas_PyObject * self, PyObject * args)
{
    evas_font_path_prepend(self->evas, ".");
    return (PyObject *) wrap_evas_object(evas_object_text_add(self->evas),
                                         self);
}

PyObject *
Evas_PyObject_object_name_find(Evas_PyObject * self, PyObject * args)
{
    char *name;
    Evas_Object *obj;
    if (!PyArg_ParseTuple(args, "s", &name))
        return NULL;

    obj = evas_object_name_find(self->evas, name);
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

    evas_font_path_clear(self->evas);
    for (i = 0; i < PyList_Size(list); i++) {
        // printf("FONT PATH %d: %s\n", i,
        // PyString_AsString(PyList_GetItem(list, i)));
        evas_font_path_append(self->evas,
                              PyString_AsString(PyList_GetItem(list, i)));
    }
    Py_INCREF(Py_None);
    return Py_None;
}

PyObject *
Evas_PyObject_damage_rectangle_add(Evas_PyObject * self, PyObject * args)
{
    int x, y, w, h;

    if (!PyArg_ParseTuple(args, "iiii", &x, &y, &w, &h))
        return NULL;

    evas_damage_rectangle_add(self->evas, x, y, w, h);
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


PyMethodDef evas_methods[] = {
    {NULL}
};

void
init_evas()
{
    PyObject *m, *c_api;
    static void *api_ptrs[2];

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

    // Export a simple API for other extension modules to be able to access
    // and manipulate Evas objects.
    api_ptrs[0] = (void *)evas_object_from_pyobject;
    api_ptrs[1] = (void *)&Evas_PyObject_Type;
    c_api = PyCObject_FromVoidPtr((void *)api_ptrs, NULL);
    PyModule_AddObject(m, "_C_API", c_api);
}

// vim: ts=4
