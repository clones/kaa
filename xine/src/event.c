#include "xine.h"
#include "event.h"
#include "event_queue.h"
#include "structmember.h"


// Owner must be a EventQueue object
Xine_Event_PyObject *
pyxine_new_event_pyobject(PyObject *owner_pyobject, xine_event_t *event, int owner)
{
    Xine_Event_PyObject *o = (Xine_Event_PyObject *)xine_object_to_pyobject_find(event);
    if (o) {
        Py_INCREF(o);
        return o;
    }

    o = (Xine_Event_PyObject *)Xine_Event_PyObject__new(&Xine_Event_PyObject_Type, NULL, NULL);
    if (!o)
        return NULL;
    if (Xine_Event_Queue_PyObject_Check(owner_pyobject))
        o->xine = ((Xine_Event_Queue_PyObject *)owner_pyobject)->xine;
    else
        PyErr_Format(xine_error, "Unsupported owner for Event object");

    o->event = event;
    o->type = PyInt_FromLong(event->type);
    o->owner_pyobject = owner_pyobject;
    Py_INCREF(owner_pyobject);

    switch (event->type) {
        case XINE_EVENT_FRAME_FORMAT_CHANGE: {
            xine_format_change_data_t *d = (xine_format_change_data_t *)event->data;
            PyDict_SetItemString_STEAL(o->data, "width", PyInt_FromLong(d->width));
            PyDict_SetItemString_STEAL(o->data, "height", PyInt_FromLong(d->height));
            PyDict_SetItemString_STEAL(o->data, "aspect", PyInt_FromLong(d->aspect));
            PyDict_SetItemString_STEAL(o->data, "pan_scan", PyInt_FromLong(d->pan_scan));
            break;
        }

        case XINE_EVENT_UI_NUM_BUTTONS: {
            xine_ui_data_t *d = (xine_ui_data_t *)event->data;
            PyDict_SetItemString_STEAL(o->data, "num_buttons", PyInt_FromLong(d->num_buttons));
            break;
        }
        case XINE_EVENT_UI_SET_TITLE: {
            xine_ui_data_t *d = (xine_ui_data_t *)event->data;
            PyDict_SetItemString_STEAL(o->data, "str", PyString_FromString(d->str));
            break;
        }
    }

    xine_object_to_pyobject_register(event, (PyObject *)o);
    return o;
}


static int
Xine_Event_PyObject__clear(Xine_Event_PyObject *self)
{
    PyObject **list[] = {NULL};
    return pyxine_gc_helper_clear(list);
}

static int
Xine_Event_PyObject__traverse(Xine_Event_PyObject *self, visitproc visit, void *arg)
{
    PyObject **list[] = {&self->owner_pyobject, NULL};
    return pyxine_gc_helper_traverse(list, visit, arg);
}

PyObject *
Xine_Event_PyObject__new(PyTypeObject *type, PyObject * args, PyObject * kwargs)
{
    Xine_Event_PyObject *self;

    if (args) {
        PyErr_SetString(xine_error, "Don't call me directly");
        return NULL;
    }

    self = (Xine_Event_PyObject *)type->tp_alloc(type, 0);
    self->data = PyDict_New();
    self->wrapper = Py_None;
    Py_INCREF(Py_None);
    return (PyObject *)self;
}

static int
Xine_Event_PyObject__init(Xine_Event_PyObject *self, PyObject *args, PyObject *kwds)
{
    return 0;
}

static PyMemberDef Xine_Event_PyObject_members[] = {
    {"owner", T_OBJECT_EX, offsetof(Xine_Event_PyObject, owner_pyobject), 0, "Owner (Queue)"},
    {"data", T_OBJECT_EX, offsetof(Xine_Event_PyObject, data), 0, "Event data"},
    {"type", T_OBJECT_EX, offsetof(Xine_Event_PyObject, type), 0, "Event type"},
    {"wrapper", T_OBJECT_EX, offsetof(Xine_Event_PyObject, wrapper), 0, "Wrapper object"},
    {NULL}
};


void
Xine_Event_PyObject__dealloc(Xine_Event_PyObject *self)
{
    //printf("DEalloc Event: %x\n", self->event);
    if (self->event && self->xine_object_owner) {
        Py_BEGIN_ALLOW_THREADS
        xine_event_free(self->event);
        Py_END_ALLOW_THREADS
    }
    Py_DECREF(self->wrapper);
    Py_DECREF(self->data);
    Py_DECREF(self->type);
    Xine_Event_PyObject__clear(self);
    Py_DECREF(self->owner_pyobject);
    xine_object_to_pyobject_unregister(self->event);
    self->ob_type->tp_free((PyObject*)self);
}

PyMethodDef Xine_Event_PyObject_methods[] = {
    {NULL, NULL}
};

PyTypeObject Xine_Event_PyObject_Type = {
    PyObject_HEAD_INIT(NULL) 
    0,                          /* ob_size */
    "_xine.Event",               /* tp_name */
    sizeof(Xine_Event_PyObject),      /* tp_basicsize */
    0,                          /* tp_itemsize */
    (destructor) Xine_Event_PyObject__dealloc,        /* tp_dealloc */
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
    "Xine Event Object",               /* tp_doc */
    (traverseproc)Xine_Event_PyObject__traverse,   /* tp_traverse */
    (inquiry)Xine_Event_PyObject__clear,           /* tp_clear */
    0,                         /* tp_richcompare */
    0,                         /* tp_weaklistoffset */
    0,                         /* tp_iter */
    0,                         /* tp_iternext */
    Xine_Event_PyObject_methods,     /* tp_methods */
    Xine_Event_PyObject_members,     /* tp_members */
    0,                         /* tp_getset */
    0,                         /* tp_base */
    0,                         /* tp_dict */
    0,                         /* tp_descr_get */
    0,                         /* tp_descr_set */
    0,                         /* tp_dictoffset */
    (initproc)Xine_Event_PyObject__init, /* tp_init */
    0,                         /* tp_alloc */
    Xine_Event_PyObject__new,        /* tp_new */
};


