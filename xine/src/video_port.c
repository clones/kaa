#include "xine.h"
#include "video_port.h"
#include "structmember.h"

static int
Xine_Video_Port_PyObject__clear(Xine_Video_Port_PyObject *self)
{
    PyObject *tmp;
    if (self->xine_pyobject) {
        tmp = self->xine_pyobject;
        self->xine_pyobject = 0;
        Py_DECREF(tmp);
    }
    return 0;
}

static int
Xine_Video_Port_PyObject__traverse(Xine_Video_Port_PyObject *self, visitproc visit, void *arg)
{
    int ret;
    if (self->xine_pyobject) {
        ret = visit((PyObject *)self->xine_pyobject, arg);
        if (ret != 0)
            return ret;
    }
    return 0;
}

PyObject *
Xine_Video_Port_PyObject__new(PyTypeObject *type, PyObject * args, PyObject * kwargs)
{
    Xine_Video_Port_PyObject *self;

    if (args) {
        PyErr_SetString(xine_error, "Don't call me directly");
        return NULL;
    }

    self = (Xine_Video_Port_PyObject *)type->tp_alloc(type, 0);
    self->owns_ref = 0;
    self->vo = NULL;
    self->xine = NULL;
    self->xine_pyobject = NULL;
    return (PyObject *)self;
}

static int
Xine_Video_Port_PyObject__init(Xine_Video_Port_PyObject *self, PyObject *args, PyObject *kwds)
{
    return 0;
}

static PyMemberDef Xine_Video_Port_PyObject_members[] = {
    {NULL}
};


void
Xine_Video_Port_PyObject__dealloc(Xine_Video_Port_PyObject *self)
{
    printf("DEalloc Video Port: %x\n", self->xine);
    if (self->vo && self->owns_ref) {
        xine_close_video_driver(self->xine, self->vo);
    }
    Xine_Video_Port_PyObject__clear(self);
    self->ob_type->tp_free((PyObject*)self);
}

// *INDENT-OFF*
PyMethodDef Xine_Video_Port_PyObject_methods[] = {
    {NULL, NULL}
};

PyTypeObject Xine_Video_Port_PyObject_Type = {
    PyObject_HEAD_INIT(NULL) 
    0,                          /* ob_size */
    "_xine.XineVideoPort",               /* tp_name */
    sizeof(Xine_Video_Port_PyObject),      /* tp_basicsize */
    0,                          /* tp_itemsize */
    (destructor) Xine_Video_Port_PyObject__dealloc,        /* tp_dealloc */
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
    "Xine Video Port Object",               /* tp_doc */
    (traverseproc)Xine_Video_Port_PyObject__traverse,   /* tp_traverse */
    (inquiry)Xine_Video_Port_PyObject__clear,           /* tp_clear */
    0,                         /* tp_richcompare */
    0,                         /* tp_weaklistoffset */
    0,                         /* tp_iter */
    0,                         /* tp_iternext */
    Xine_Video_Port_PyObject_methods,     /* tp_methods */
    Xine_Video_Port_PyObject_members,     /* tp_members */
    0,                         /* tp_getset */
    0,                         /* tp_base */
    0,                         /* tp_dict */
    0,                         /* tp_descr_get */
    0,                         /* tp_descr_set */
    0,                         /* tp_dictoffset */
    (initproc)Xine_Video_Port_PyObject__init, /* tp_init */
    0,                         /* tp_alloc */
    Xine_Video_Port_PyObject__new,        /* tp_new */
};


