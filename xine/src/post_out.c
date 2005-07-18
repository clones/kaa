#include "xine.h"
#include "post_out.h"
#include "post.h"
#include "video_port.h"
#include "audio_port.h"
#include "post_in.h"
#include "structmember.h"

Xine_Post_Out_PyObject *
pyxine_new_post_out_pyobject(Xine_Post_PyObject *post, xine_post_out_t *post_out, 
                         int owner)
{
    Xine_Post_Out_PyObject *o = (Xine_Post_Out_PyObject *)xine_object_to_pyobject_find(post_out);
    if (o) {
        Py_INCREF(o);
        return o;
    }
    o = (Xine_Post_Out_PyObject *)Xine_Post_Out_PyObject__new(&Xine_Post_Out_PyObject_Type, NULL, NULL);
    if (!o)
        return NULL;
    o->post_out = post_out;

    if (!post)
        post = (Xine_Post_PyObject *)Py_None;
    o->post_pyobject = (PyObject *)post;
    Py_INCREF(post);
    o->xine_object_owner = owner;
    xine_object_to_pyobject_register(post_out, (PyObject *)o);
    return o;
}


static int
Xine_Post_Out_PyObject__clear(Xine_Post_Out_PyObject *self)
{
    PyObject *tmp;
    if (self->post_pyobject) {
        tmp = self->post_pyobject;
        self->post_pyobject = 0;
        Py_DECREF(tmp);
    }
    return 0;
}

static int
Xine_Post_Out_PyObject__traverse(Xine_Post_Out_PyObject *self, visitproc visit, void *arg)
{
    int ret;
    if (self->post_pyobject) {
        ret = visit((PyObject *)self->post_pyobject, arg);
        if (ret != 0)
            return ret;
    }
}

PyObject *
Xine_Post_Out_PyObject__new(PyTypeObject *type, PyObject * args, PyObject * kwargs)
{
    Xine_Post_Out_PyObject *self;

    if (args) {
        PyErr_SetString(xine_error, "Don't call me directly");
        return NULL;
    }

    self = (Xine_Post_Out_PyObject *)type->tp_alloc(type, 0);
    self->post_out = NULL;
    self->post_pyobject = NULL;
    self->wrapper = Py_None;
    Py_INCREF(Py_None);
    return (PyObject *)self;
}

static int
Xine_Post_Out_PyObject__init(Xine_Post_Out_PyObject *self, PyObject *args, PyObject *kwds)
{
    return 0;
}

static PyMemberDef Xine_Post_Out_PyObject_members[] = {
    {"post", T_OBJECT_EX, offsetof(Xine_Post_Out_PyObject, post_pyobject), 0, "Post object"},
    {"wrapper", T_OBJECT_EX, offsetof(Xine_Post_Out_PyObject, wrapper), 0, "Wrapper object"},
    {NULL}
};


void
Xine_Post_Out_PyObject__dealloc(Xine_Post_Out_PyObject *self)
{
    printf("DEalloc Post Out: %x\n", self->post_out);
    if (self->post_out && self->xine_object_owner) {
    }
    Py_DECREF(self->wrapper);
    Xine_Post_Out_PyObject__clear(self);
    xine_object_to_pyobject_unregister(self->post_out);
    self->ob_type->tp_free((PyObject*)self);
}


PyObject *
Xine_Post_Out_PyObject_wire(Xine_Post_Out_PyObject *self, PyObject *args, PyObject *kwargs)
{
    Xine_Post_In_PyObject *input;
    int result;

    if (!PyArg_ParseTuple(args, "O!", &Xine_Post_In_PyObject_Type, &input))
        return NULL;

    result = xine_post_wire(self->post_out, input->post_in);
    return PyBool_FromLong(result);
}

PyObject *
Xine_Post_Out_PyObject_wire_video_port(Xine_Post_Out_PyObject *self, PyObject *args, PyObject *kwargs)
{
    Xine_Video_Port_PyObject *port;
    int result;

    if (!PyArg_ParseTuple(args, "O!", &Xine_Video_Port_PyObject_Type, &port))
        return NULL;

    result = xine_post_wire_video_port(self->post_out, port->vo);
    return PyBool_FromLong(result);
}

PyObject *
Xine_Post_Out_PyObject_wire_audio_port(Xine_Post_Out_PyObject *self, PyObject *args, PyObject *kwargs)
{
    Xine_Audio_Port_PyObject *port;
    int result;

    if (!PyArg_ParseTuple(args, "O!", &Xine_Audio_Port_PyObject_Type, &port))
        return NULL;

    result = xine_post_wire_audio_port(self->post_out, port->ao);
    return PyBool_FromLong(result);
}


PyMethodDef Xine_Post_Out_PyObject_methods[] = {
    {"wire", (PyCFunction) Xine_Post_Out_PyObject_wire, METH_VARARGS},
    {"wire_video_port", (PyCFunction) Xine_Post_Out_PyObject_wire_video_port, METH_VARARGS},
    {"wire_audio_port", (PyCFunction) Xine_Post_Out_PyObject_wire_audio_port, METH_VARARGS},
    {NULL, NULL}
};

PyTypeObject Xine_Post_Out_PyObject_Type = {
    PyObject_HEAD_INIT(NULL) 
    0,                          /* ob_size */
    "_xine.PostOut",               /* tp_name */
    sizeof(Xine_Post_Out_PyObject),      /* tp_basicsize */
    0,                          /* tp_itemsize */
    (destructor) Xine_Post_Out_PyObject__dealloc,        /* tp_dealloc */
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
    "Xine Post Output Object",               /* tp_doc */
    (traverseproc)Xine_Post_Out_PyObject__traverse,   /* tp_traverse */
    (inquiry)Xine_Post_Out_PyObject__clear,           /* tp_clear */
    0,                         /* tp_richcompare */
    0,                         /* tp_weaklistoffset */
    0,                         /* tp_iter */
    0,                         /* tp_iternext */
    Xine_Post_Out_PyObject_methods,     /* tp_methods */
    Xine_Post_Out_PyObject_members,     /* tp_members */
    0,                         /* tp_getset */
    0,                         /* tp_base */
    0,                         /* tp_dict */
    0,                         /* tp_descr_get */
    0,                         /* tp_descr_set */
    0,                         /* tp_dictoffset */
    (initproc)Xine_Post_Out_PyObject__init, /* tp_init */
    0,                         /* tp_alloc */
    Xine_Post_Out_PyObject__new,        /* tp_new */
};


