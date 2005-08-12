#include "xine.h"
#include "stream.h"
#include "post.h"
#include "post_in.h"
#include "structmember.h"

// Owner must be a Post object
Xine_Post_In_PyObject *
pyxine_new_post_in_pyobject(PyObject *owner_pyobject, xine_post_in_t *post_in, 
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

    if (Xine_Post_PyObject_Check(owner_pyobject))
        o->xine = ((Xine_Post_PyObject *)owner_pyobject)->xine;
    else
        PyErr_Format(xine_error, "Unsupported owner for PostIn object");


    o->owner_pyobject = owner_pyobject;
    Py_INCREF(owner_pyobject);

    o->post_in = post_in;
    o->xine_object_owner = owner;
    xine_object_to_pyobject_register(post_in, (PyObject *)o);

    // Create Port object for this PostIn
    if (post_in->type == XINE_POST_DATA_VIDEO) {
        if (post_in->data) {
            xine_video_port_t *vo = (xine_video_port_t *)post_in->data;
            o->port = (PyObject *)pyxine_new_video_port_pyobject((PyObject *)o, vo, NULL, 0);
        }
    }
    else if (post_in->type == XINE_POST_DATA_AUDIO) {
        if (post_in->data) {
            xine_audio_port_t *ao = (xine_audio_port_t *)post_in->data;
            o->port = (PyObject *)pyxine_new_audio_port_pyobject((PyObject *)o, ao, 0);
        }
    }
    else {
        o->port = Py_None;
        Py_INCREF(Py_None);
//        printf("!!! Unsupported PostIn data type: %d\n", post_in->type);
    }

    return o;
}


static int
Xine_Post_In_PyObject__clear(Xine_Post_In_PyObject *self)
{
    PyObject **list[] = {&self->owner_pyobject, &self->wrapper, &self->port, NULL};
    return pyxine_gc_helper_clear(list);

}

static int
Xine_Post_In_PyObject__traverse(Xine_Post_In_PyObject *self, visitproc visit, void *arg)
{
    PyObject **list[] = {&self->owner_pyobject, &self->wrapper, &self->port, NULL};
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
    self->owner_pyobject = NULL;
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
    {"port", T_OBJECT_EX, offsetof(Xine_Post_In_PyObject, port), 0, "Video/Audio Port"},
    {"owner", T_OBJECT_EX, offsetof(Xine_Post_In_PyObject, owner_pyobject), 0, "Owner"},
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


PyObject *
Xine_Post_In_PyObject_get_type(Xine_Post_In_PyObject *self, PyObject *args, PyObject *kwargs)
{
    return PyInt_FromLong(self->post_in->type);
}

PyObject *
Xine_Post_In_PyObject_get_name(Xine_Post_In_PyObject *self, PyObject *args, PyObject *kwargs)
{
    return Py_BuildValue("z", self->post_in->name);
}

PyObject *
Xine_Post_In_PyObject_get_port(Xine_Post_In_PyObject *self, PyObject *args, PyObject *kwargs)
{
    Py_INCREF(self->port);
    return self->port;
}

PyMethodDef Xine_Post_In_PyObject_methods[] = {
    {"get_type", (PyCFunction) Xine_Post_In_PyObject_get_type, METH_VARARGS},
    {"get_name", (PyCFunction) Xine_Post_In_PyObject_get_name, METH_VARARGS},
    {"get_port", (PyCFunction) Xine_Post_In_PyObject_get_port, METH_VARARGS},

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


