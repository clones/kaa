#include "xine.h"
#include "stream.h"
#include "event_queue.h"
#include "structmember.h"


// Owner must be a Stream object
Xine_Event_Queue_PyObject *
pyxine_new_event_queue_pyobject(PyObject *owner_pyobject, xine_event_queue_t *queue, int owner)
{
    Xine_Event_Queue_PyObject *o = (Xine_Event_Queue_PyObject *)xine_object_to_pyobject_find(queue);
    if (o) {
        Py_INCREF(o);
        return o;
    }

    o = (Xine_Event_Queue_PyObject *)Xine_Event_Queue_PyObject__new(&Xine_Event_Queue_PyObject_Type, NULL, NULL);
    if (!o)
        return NULL;
    o->queue = queue;
    o->owner_pyobject = owner_pyobject;
    Py_INCREF(owner_pyobject);

    if (Xine_Stream_PyObject_Check(owner_pyobject))
        o->xine = ((Xine_Stream_PyObject *)owner_pyobject)->xine;
    else
        PyErr_Format(xine_error, "Unsupported owner for AudioPort object");

    xine_object_to_pyobject_register(queue, (PyObject *)o);
    return o;
}


static int
Xine_Event_Queue_PyObject__clear(Xine_Event_Queue_PyObject *self)
{
    PyObject **list[] = {&self->owner_pyobject, NULL};
    return pyxine_gc_helper_clear(list);
}

static int
Xine_Event_Queue_PyObject__traverse(Xine_Event_Queue_PyObject *self, visitproc visit, void *arg)
{
    PyObject **list[] = {&self->owner_pyobject, NULL};
    return pyxine_gc_helper_traverse(list, visit, arg);
}

PyObject *
Xine_Event_Queue_PyObject__new(PyTypeObject *type, PyObject * args, PyObject * kwargs)
{
    Xine_Event_Queue_PyObject *self;

    if (args) {
        PyErr_SetString(xine_error, "Don't call me directly");
        return NULL;
    }

    self = (Xine_Event_Queue_PyObject *)type->tp_alloc(type, 0);
    self->wrapper = Py_None;
    Py_INCREF(Py_None);
    return (PyObject *)self;
}

static int
Xine_Event_Queue_PyObject__init(Xine_Event_Queue_PyObject *self, PyObject *args, PyObject *kwds)
{
    return 0;
}

static PyMemberDef Xine_Event_Queue_PyObject_members[] = {
    {"owner", T_OBJECT_EX, offsetof(Xine_Event_Queue_PyObject, owner_pyobject), 0, "Owner"},
    {"wrapper", T_OBJECT_EX, offsetof(Xine_Event_Queue_PyObject, wrapper), 0, "Wrapper object"},
    {NULL}
};


void
Xine_Event_Queue_PyObject__dealloc(Xine_Event_Queue_PyObject *self)
{
    printf("DEalloc Event Queue: %x\n", self->queue);
    if (self->queue && self->xine_object_owner) {
        Py_BEGIN_ALLOW_THREADS
        xine_event_dispose_queue(self->queue);
        Py_END_ALLOW_THREADS
    }
    Py_DECREF(self->wrapper);
    Xine_Event_Queue_PyObject__clear(self);
    xine_object_to_pyobject_unregister(self->queue);
    self->ob_type->tp_free((PyObject*)self);
}

PyMethodDef Xine_Event_Queue_PyObject_methods[] = {
    {NULL, NULL}
};

PyTypeObject Xine_Event_Queue_PyObject_Type = {
    PyObject_HEAD_INIT(NULL) 
    0,                          /* ob_size */
    "_xine.EventQueue",               /* tp_name */
    sizeof(Xine_Event_Queue_PyObject),      /* tp_basicsize */
    0,                          /* tp_itemsize */
    (destructor) Xine_Event_Queue_PyObject__dealloc,        /* tp_dealloc */
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
    "Xine Event Queue Object",               /* tp_doc */
    (traverseproc)Xine_Event_Queue_PyObject__traverse,   /* tp_traverse */
    (inquiry)Xine_Event_Queue_PyObject__clear,           /* tp_clear */
    0,                         /* tp_richcompare */
    0,                         /* tp_weaklistoffset */
    0,                         /* tp_iter */
    0,                         /* tp_iternext */
    Xine_Event_Queue_PyObject_methods,     /* tp_methods */
    Xine_Event_Queue_PyObject_members,     /* tp_members */
    0,                         /* tp_getset */
    0,                         /* tp_base */
    0,                         /* tp_dict */
    0,                         /* tp_descr_get */
    0,                         /* tp_descr_set */
    0,                         /* tp_dictoffset */
    (initproc)Xine_Event_Queue_PyObject__init, /* tp_init */
    0,                         /* tp_alloc */
    Xine_Event_Queue_PyObject__new,        /* tp_new */
};


