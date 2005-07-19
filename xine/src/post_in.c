#include "xine.h"
#include "post.h"
#include "post_in.h"
#include "structmember.h"

Xine_Post_In_PyObject *
pyxine_new_post_in_pyobject(Xine_Post_PyObject *post, xine_post_in_t *post_in, 
                         int owner)
{
    Xine_Post_In_PyObject *o = (Xine_Post_In_PyObject *)xine_object_to_pyobject_find(post_in);
    if (o) {
        Py_INCREF(o);
        return o;
    }
    o = (Xine_Post_In_PyObject *)Xine_Post_In_PyObject__new(&Xine_Post_In_PyObject_Type, NULL, NULL);
    if (!o)
        return NULL;
    o->post_in = post_in;
    o->post_pyobject = (PyObject *)post;
    Py_INCREF(post);
    o->xine_object_owner = owner;
    xine_object_to_pyobject_register(post_in, (PyObject *)o);
    return o;
}


static int
Xine_Post_In_PyObject__clear(Xine_Post_In_PyObject *self)
{
    PyObject **list[] = {&self->post_pyobject, &self->wrapper, NULL};
    return pyxine_gc_helper_clear(list);

}

static int
Xine_Post_In_PyObject__traverse(Xine_Post_In_PyObject *self, visitproc visit, void *arg)
{
    PyObject **list[] = {&self->post_pyobject, &self->wrapper, NULL};
    return pyxine_gc_helper_traverse(list, visit, arg);
}

PyObject *
Xine_Post_In_PyObject__new(PyTypeObject *type, PyObject * args, PyObject * kwargs)
{
    Xine_Post_In_PyObject *self;

    if (args) {
        PyErr_SetString(xine_error, "Don't call me directly");
        return NULL;
    }

    self = (Xine_Post_In_PyObject *)type->tp_alloc(type, 0);
    self->post_in = NULL;
    self->post_pyobject = NULL;
    self->wrapper = Py_None;
    Py_INCREF(Py_None);
    return (PyObject *)self;
}

static int
Xine_Post_In_PyObject__init(Xine_Post_In_PyObject *self, PyObject *args, PyObject *kwds)
{
    return 0;
}

static PyMemberDef Xine_Post_In_PyObject_members[] = {
    {"post", T_OBJECT_EX, offsetof(Xine_Post_In_PyObject, post_pyobject), 0, "Post object"},
    {"wrapper", T_OBJECT_EX, offsetof(Xine_Post_In_PyObject, wrapper), 0, "Wrapper object"},
    {NULL}
};


void
Xine_Post_In_PyObject__dealloc(Xine_Post_In_PyObject *self)
{
    printf("DEalloc Post In: %x\n", self->post_in);
    if (self->post_in && self->xine_object_owner) {
    }
    Xine_Post_In_PyObject__clear(self);
    xine_object_to_pyobject_unregister(self->post_in);
    self->ob_type->tp_free((PyObject*)self);
}


// *INDENT-OFF*
PyMethodDef Xine_Post_In_PyObject_methods[] = {
//    {"get_identifier", (PyCFunction) Xine_Post_In_PyObject_get_identifer, METH_VARARGS},

    {NULL, NULL}
};

PyTypeObject Xine_Post_In_PyObject_Type = {
    PyObject_HEAD_INIT(NULL) 
    0,                          /* ob_size */
    "_xine.PostIn",               /* tp_name */
    sizeof(Xine_Post_In_PyObject),      /* tp_basicsize */
    0,                          /* tp_itemsize */
    (destructor) Xine_Post_In_PyObject__dealloc,        /* tp_dealloc */
    0,                          /* tp_print */
    0,                          /* tp_getattr */
    0,                          /* tp_setattr */
    0,                          /* tp_compare */
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
    "Xine Post Input Object",               /* tp_doc */
    (traverseproc)Xine_Post_In_PyObject__traverse,   /* tp_traverse */
    (inquiry)Xine_Post_In_PyObject__clear,           /* tp_clear */
    0,                         /* tp_richcompare */
    0,                         /* tp_weaklistoffset */
    0,                         /* tp_iter */
    0,                         /* tp_iternext */
    Xine_Post_In_PyObject_methods,     /* tp_methods */
    Xine_Post_In_PyObject_members,     /* tp_members */
    0,                         /* tp_getset */
    0,                         /* tp_base */
    0,                         /* tp_dict */
    0,                         /* tp_descr_get */
    0,                         /* tp_descr_set */
    0,                         /* tp_dictoffset */
    (initproc)Xine_Post_In_PyObject__init, /* tp_init */
    0,                         /* tp_alloc */
    Xine_Post_In_PyObject__new,        /* tp_new */
};


