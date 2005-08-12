#include "xine.h"
#include "post.h"
#include "post_in.h"
#include "post_out.h"
#include "stream.h"
#include "video_port.h"
#include "structmember.h"

// Owner must be a Post In, Post Out, Xine, or Stream object
Xine_Video_Port_PyObject *
pyxine_new_video_port_pyobject(PyObject *owner_pyobject, xine_video_port_t * vo, PyObject *driver, int owner)
{
    Xine_Video_Port_PyObject *o = (Xine_Video_Port_PyObject *)xine_object_to_pyobject_find(vo);
    if (o) {
        Py_INCREF(o);
        return o;
    }

    o = (Xine_Video_Port_PyObject *)
        Xine_Video_Port_PyObject__new(&Xine_Video_Port_PyObject_Type, NULL, NULL);
    if (!o)
        return NULL;

    if (Xine_PyObject_Check(owner_pyobject))
        o->xine = ((Xine_PyObject *)owner_pyobject)->xine;
    else if (Xine_Post_PyObject_Check(owner_pyobject)) {
        printf(" *** deprecated: pyxine_new_video_port_pyobject got a Post object -- use Post In/Out instead\n");
        o->xine = ((Xine_Post_PyObject *)owner_pyobject)->xine;
    }
    else if (Xine_Post_In_PyObject_Check(owner_pyobject))
        o->xine = ((Xine_Post_In_PyObject *)owner_pyobject)->xine;
    else if (Xine_Post_Out_PyObject_Check(owner_pyobject))
        o->xine = ((Xine_Post_Out_PyObject *)owner_pyobject)->xine;
    else if (Xine_Stream_PyObject_Check(owner_pyobject))
        o->xine = ((Xine_Stream_PyObject *)owner_pyobject)->xine;
    else
        PyErr_Format(xine_error, "Unsupported owner for VideoPort object");

    o->owner_pyobject = owner_pyobject;
    Py_INCREF(owner_pyobject);

    if (driver)
        o->driver = driver;
    else
        o->driver = Py_None;
    Py_INCREF(o->driver);

    o->vo = vo;
    o->xine_object_owner = owner;
    xine_object_to_pyobject_register(vo, (PyObject *)o);
    return o;
}



static int
Xine_Video_Port_PyObject__clear(Xine_Video_Port_PyObject * self)
{
    PyObject **list[] = {&self->owner_pyobject, &self->wire_list, NULL};
    return pyxine_gc_helper_clear(list);
}

static int
Xine_Video_Port_PyObject__traverse(Xine_Video_Port_PyObject * self,
                                   visitproc visit, void *arg)
{
    PyObject **list[] = {&self->owner_pyobject, &self->wire_list, &self->driver, NULL};
    return pyxine_gc_helper_traverse(list, visit, arg);
}

PyObject *
Xine_Video_Port_PyObject__new(PyTypeObject * type, PyObject * args,
                              PyObject * kwargs)
{
    Xine_Video_Port_PyObject *self;

    if (args) {
        PyErr_SetString(xine_error, "Don't call me directly");
        return NULL;
    }

    self = (Xine_Video_Port_PyObject *) type->tp_alloc(type, 0);
    self->vo = NULL;
    self->xine = NULL;
    self->owner_pyobject = NULL;
    self->wire_list = PyList_New(0);
    self->wrapper = Py_None;
    Py_INCREF(Py_None);
    return (PyObject *) self;
}

static int
Xine_Video_Port_PyObject__init(Xine_Video_Port_PyObject * self,
                               PyObject * args, PyObject * kwds)
{
    return 0;
}

static PyMemberDef Xine_Video_Port_PyObject_members[] = {
    {"driver", T_OBJECT_EX, offsetof(Xine_Video_Port_PyObject, driver), 0, "Video Driver object of this port"},
    {"wire_list", T_OBJECT_EX, offsetof(Xine_Video_Port_PyObject, wire_list), 0, "List of wired PostOut objects"},
    {"owner", T_OBJECT_EX, offsetof(Xine_Video_Port_PyObject, owner_pyobject), 0, "Owner"},
    {"wrapper", T_OBJECT_EX, offsetof(Xine_Video_Port_PyObject, wrapper), 0, "Wrapper object"},
    {NULL}
};


void
Xine_Video_Port_PyObject__dealloc(Xine_Video_Port_PyObject * self)
{
    printf("DEalloc Video Port: %x, driver=%x (%d) owner=%s \n", self->vo, 
            ((xine_video_port_t *)self->vo)->driver, self->xine_object_owner,
            self->owner_pyobject->ob_type->tp_name);
    if (self->vo && self->xine_object_owner) {
        Py_BEGIN_ALLOW_THREADS
        xine_close_video_driver(self->xine, self->vo);
        Py_END_ALLOW_THREADS
    }
    Py_DECREF(self->driver);
    Py_DECREF(self->wrapper);
    Xine_Video_Port_PyObject__clear(self);
    xine_object_to_pyobject_unregister(self->vo);

    self->ob_type->tp_free((PyObject *) self);
}



PyObject *
Xine_Video_Port_PyObject_send_gui_data(Xine_Video_Port_PyObject *self, PyObject *args, PyObject *kwargs)
{
    int type, data, result;

    if (!PyArg_ParseTuple(args, "ii", &type, &data))
        return NULL;

    result = xine_port_send_gui_data(self->vo, type, (void *)data);
    return PyInt_FromLong(result);
}


PyMethodDef Xine_Video_Port_PyObject_methods[] = {
    {"send_gui_data", (PyCFunction) Xine_Video_Port_PyObject_send_gui_data, METH_VARARGS },
    {NULL, NULL}
};

PyTypeObject Xine_Video_Port_PyObject_Type = {
    PyObject_HEAD_INIT(NULL) 
    0,                          /* ob_size */
    "_xine.VideoPort",               /* tp_name */
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


