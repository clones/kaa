#include "xine.h"
#include "post.h"
#include "post_in.h"
#include "post_out.h"
#include "audio_port.h"
#include "stream.h"
#include "structmember.h"


// Owner must be a Post In, Post Out, Xine, or Stream object
// XXX: if Xine, must be driver -- owner param deprecated then?
Xine_Audio_Port_PyObject *
pyxine_new_audio_port_pyobject(PyObject *owner_pyobject, xine_audio_port_t *ao, int owner)
{
    Xine_Audio_Port_PyObject *o = (Xine_Audio_Port_PyObject *)xine_object_to_pyobject_find(ao);
    if (o) {
        Py_INCREF(o);
        return o;
    }

    o = (Xine_Audio_Port_PyObject *)Xine_Audio_Port_PyObject__new(&Xine_Audio_Port_PyObject_Type, NULL, NULL);
    if (!o)
        return NULL;

    if (Xine_PyObject_Check(owner_pyobject))
        o->xine = ((Xine_PyObject *)owner_pyobject)->xine;
    else if (Xine_Post_In_PyObject_Check(owner_pyobject))
        o->xine = ((Xine_Post_In_PyObject *)owner_pyobject)->xine;
    else if (Xine_Post_Out_PyObject_Check(owner_pyobject))
        o->xine = ((Xine_Post_Out_PyObject *)owner_pyobject)->xine;
    else if (Xine_Stream_PyObject_Check(owner_pyobject))
        o->xine = ((Xine_Stream_PyObject *)owner_pyobject)->xine;
    else
        PyErr_Format(xine_error, "Unsupported owner for AudioPort object");

    o->ao = ao;
    o->owner_pyobject = owner_pyobject;
    Py_INCREF(owner_pyobject);

    xine_object_to_pyobject_register(ao, (PyObject *)o);
    return o;
}


static int
Xine_Audio_Port_PyObject__clear(Xine_Audio_Port_PyObject *self)
{
    PyObject **list[] = {&self->owner_pyobject, &self->wire_object, NULL};
    return pyxine_gc_helper_clear(list);
}

static int
Xine_Audio_Port_PyObject__traverse(Xine_Audio_Port_PyObject *self, visitproc visit, void *arg)
{
    PyObject **list[] = {&self->owner_pyobject, &self->wire_object, NULL};
    return pyxine_gc_helper_traverse(list, visit, arg);
}

PyObject *
Xine_Audio_Port_PyObject__new(PyTypeObject *type, PyObject * args, PyObject * kwargs)
{
    Xine_Audio_Port_PyObject *self;

    if (args) {
        PyErr_SetString(xine_error, "Don't call me directly");
        return NULL;
    }

    self = (Xine_Audio_Port_PyObject *)type->tp_alloc(type, 0);
    self->ao = NULL;
    self->xine = NULL;
    self->wire_object = self->wrapper = Py_None;
    Py_INCREF(Py_None);
    Py_INCREF(Py_None);
    return (PyObject *)self;
}

static int
Xine_Audio_Port_PyObject__init(Xine_Audio_Port_PyObject *self, PyObject *args, PyObject *kwds)
{
    return 0;
}

static PyMemberDef Xine_Audio_Port_PyObject_members[] = {
    {"wire_object", T_OBJECT_EX, offsetof(Xine_Audio_Port_PyObject, wire_object), 0, "Object wired to"},
    {"owner", T_OBJECT_EX, offsetof(Xine_Audio_Port_PyObject, owner_pyobject), 0, "Owner"},
    {"wrapper", T_OBJECT_EX, offsetof(Xine_Audio_Port_PyObject, wrapper), 0, "Wrapper object"},
    {NULL}
};


void
Xine_Audio_Port_PyObject__dealloc(Xine_Audio_Port_PyObject *self)
{
    printf("DEalloc Audio Port: %x\n", self->ao);
    if (self->ao && self->xine_object_owner) {
        Py_BEGIN_ALLOW_THREADS
        xine_close_audio_driver(self->xine, self->ao);
        Py_END_ALLOW_THREADS
    }
    Py_DECREF(self->wrapper);
    Xine_Audio_Port_PyObject__clear(self);
    xine_object_to_pyobject_unregister(self->ao);
    self->ob_type->tp_free((PyObject*)self);
}

// *INDENT-OFF*
PyMethodDef Xine_Audio_Port_PyObject_methods[] = {
    {NULL, NULL}
};

PyTypeObject Xine_Audio_Port_PyObject_Type = {
    PyObject_HEAD_INIT(NULL) 
    0,                          /* ob_size */
    "_xine.AudioPort",               /* tp_name */
    sizeof(Xine_Audio_Port_PyObject),      /* tp_basicsize */
    0,                          /* tp_itemsize */
    (destructor) Xine_Audio_Port_PyObject__dealloc,        /* tp_dealloc */
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
    "Xine Audio Port Object",               /* tp_doc */
    (traverseproc)Xine_Audio_Port_PyObject__traverse,   /* tp_traverse */
    (inquiry)Xine_Audio_Port_PyObject__clear,           /* tp_clear */
    0,                         /* tp_richcompare */
    0,                         /* tp_weaklistoffset */
    0,                         /* tp_iter */
    0,                         /* tp_iternext */
    Xine_Audio_Port_PyObject_methods,     /* tp_methods */
    Xine_Audio_Port_PyObject_members,     /* tp_members */
    0,                         /* tp_getset */
    0,                         /* tp_base */
    0,                         /* tp_dict */
    0,                         /* tp_descr_get */
    0,                         /* tp_descr_set */
    0,                         /* tp_dictoffset */
    (initproc)Xine_Audio_Port_PyObject__init, /* tp_init */
    0,                         /* tp_alloc */
    Xine_Audio_Port_PyObject__new,        /* tp_new */
};


