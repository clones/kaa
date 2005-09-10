#include "xine.h"
#include "post.h"
#include "post_out.h"
#include "post_in.h"
#include "video_port.h"
#include "audio_port.h"
#include "stream.h"
#include "structmember.h"

void _post_out_set_port(Xine_Post_Out_PyObject *);

// Owner must be a Post or Stream object
Xine_Post_Out_PyObject *
pyxine_new_post_out_pyobject(Xine_PyObject *xine, void *owner, xine_post_out_t *post_out, int do_dispose)
{
    Xine_Post_Out_PyObject *o;
    PyObject *owner_pyobject;

    o = (Xine_Post_Out_PyObject *)xine_object_to_pyobject_find(post_out);
    if (o) {
        Py_INCREF(o);
        return o;
    }

    // Verify owner
    owner_pyobject = xine_object_to_pyobject_find(owner);
    if (!owner_pyobject || 
        (!Xine_Post_PyObject_Check(owner_pyobject) &&
         !Xine_Stream_PyObject_Check(owner_pyobject))) {
            PyErr_Format(xine_error, "Unsupported owner for PostOut object");
            return NULL;
    }

    o = (Xine_Post_Out_PyObject *)Xine_Post_Out_PyObject__new(&Xine_Post_Out_PyObject_Type, NULL, NULL);
    if (!o)
        return NULL;
     
    o->post_out = post_out;
    o->do_dispose = do_dispose;
    o->owner = owner;
    o->xine = xine;
    Py_INCREF(xine);

    xine_object_to_pyobject_register(post_out, (PyObject *)o);

    _post_out_set_port(o);

    return o;
}

PyObject *
_get_wire_list_from_port(PyObject *port)
{
    if (port && Xine_Video_Port_PyObject_Check(port))
        return ((Xine_Video_Port_PyObject *)port)->wire_list;
    else if (port && Xine_Audio_Port_PyObject_Check(port))
        return ((Xine_Audio_Port_PyObject *)port)->wire_list;
    return NULL;
}

void
_post_out_port_unlink(Xine_Post_Out_PyObject *self)
{
    PyObject *wire_list, *objid;

    objid = PyLong_FromLong((long)self->post_out);
    wire_list = _get_wire_list_from_port(self->port);
    if (wire_list && PySequence_Contains(wire_list, objid))
        PySequence_DelItem(wire_list, PySequence_Index(wire_list, objid));
    Py_DECREF(objid);
    Py_DECREF(self->port);
}

void
_post_out_set_port(Xine_Post_Out_PyObject *self)
{
    xine_video_port_t *vo;
    xine_audio_port_t *ao;
    PyObject *owner_pyobject, *port, *wire_list, *objid;

    // Return the video/audio port that we are wired to.  Streams are special
    // cases, since the data field of the xine_post_out_t seems to point to a
    // Xine object.  So we check to see if we're owned by a Steam, and if so,
    // fetch the video_out/audio_out field from xine_stream_t instead.

    owner_pyobject = xine_object_to_pyobject_find(self->owner);
    if (self->post_out->type == XINE_POST_DATA_VIDEO) {
        if (self->post_out->data && *(void **)self->post_out->data) {
            if (Xine_Stream_PyObject_Check(owner_pyobject))
                vo = ((Xine_Stream_PyObject *)owner_pyobject)->stream->video_out;
            else
                vo = *(xine_video_port_t **)self->post_out->data;
            port = (PyObject *)pyxine_new_video_port_pyobject(self->xine, self->post_out, vo, NULL, 0);
        }
    }
    else if (self->post_out->type == XINE_POST_DATA_AUDIO) {
        if (self->post_out->data && *(void **)self->post_out->data) {
            if (Xine_Stream_PyObject_Check(owner_pyobject))
                ao = ((Xine_Stream_PyObject *)owner_pyobject)->stream->audio_out;
            else
                ao = *(xine_audio_port_t **)self->post_out->data;
            port = (PyObject *)pyxine_new_audio_port_pyobject(self->xine, self->post_out, ao, 0);
        }
    }
    else {
        port = Py_None;
        Py_INCREF(port);
    }

    if (self->port == port) {
        Py_DECREF(port);
        return;
    }

    _post_out_port_unlink(self);

    self->port = port;

    objid = PyLong_FromLong((long)self->post_out);
    wire_list = _get_wire_list_from_port(self->port);
    if (wire_list && !PySequence_Contains(wire_list, objid))
        PyList_Append(wire_list, objid);
    Py_DECREF(objid);

}

/*
static int
Xine_Post_Out_PyObject__clear(Xine_Post_Out_PyObject *self)
{
    PyObject **list[] = {&self->owner_pyobject, &self->wrapper, NULL};
    return pyxine_gc_helper_clear(list);
}

static int
Xine_Post_Out_PyObject__traverse(Xine_Post_Out_PyObject *self, visitproc visit, void *arg)
{
    PyObject **list[] = {&self->owner_pyobject, &self->wrapper, NULL};
    return pyxine_gc_helper_traverse(list, visit, arg);
}
*/
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
    self->xine = NULL;

    self->port = self->wrapper = Py_None;
    Py_INCREF(Py_None);
    Py_INCREF(Py_None);
    return (PyObject *)self;
}

static int
Xine_Post_Out_PyObject__init(Xine_Post_Out_PyObject *self, PyObject *args, PyObject *kwds)
{
    return 0;
}

static PyMemberDef Xine_Post_Out_PyObject_members[] = {
    {"wrapper", T_OBJECT_EX, offsetof(Xine_Post_Out_PyObject, wrapper), 0, "Wrapper object"},
    {"port", T_OBJECT_EX, offsetof(Xine_Post_Out_PyObject, port), 0, "Video/Audio port wired"},
    {NULL}
};


void
Xine_Post_Out_PyObject__dealloc(Xine_Post_Out_PyObject *self)
{
    printf("DEalloc Post Out: %x\n", self->post_out);
    if (self->post_out && self->do_dispose) {
    }
    //Xine_Post_Out_PyObject__clear(self);
    _post_out_port_unlink(self);
    //Py_DECREF(self->port);
    Py_DECREF(self->wrapper);
    Py_DECREF(self->xine);
    xine_object_to_pyobject_unregister(self->post_out);
    self->ob_type->tp_free((PyObject*)self);
}

PyObject *
Xine_Post_Out_PyObject_get_owner(Xine_Post_Out_PyObject *self, PyObject *args, PyObject *kwargs)
{
    PyObject *owner = xine_object_to_pyobject_find(self->owner);
    if (!owner)
        owner = Py_None;
    Py_INCREF(owner);
    return owner;
}

PyObject *
Xine_Post_Out_PyObject_get_port(Xine_Post_Out_PyObject *self, PyObject *args, PyObject *kwargs)
{
    Py_INCREF(self->port);
    return self->port;
}

PyObject *
Xine_Post_Out_PyObject_get_type(Xine_Post_Out_PyObject *self, PyObject *args, PyObject *kwargs)
{
    return PyInt_FromLong(self->post_out->type);
}

PyObject *
Xine_Post_Out_PyObject_get_name(Xine_Post_Out_PyObject *self, PyObject *args, PyObject *kwargs)
{
    return Py_BuildValue("z", self->post_out->name);
}



PyObject *
Xine_Post_Out_PyObject_wire(Xine_Post_Out_PyObject *self, PyObject *args, PyObject *kwargs)
{
    Xine_Post_In_PyObject *input;
    int result;

    if (!PyArg_ParseTuple(args, "O!", &Xine_Post_In_PyObject_Type, &input))
        return NULL;

    Py_BEGIN_ALLOW_THREADS
    result = xine_post_wire(self->post_out, input->post_in);
    Py_END_ALLOW_THREADS
    _post_out_set_port(self);
    return PyBool_FromLong(result);
}

PyObject *
Xine_Post_Out_PyObject_wire_video_port(Xine_Post_Out_PyObject *self, PyObject *args, PyObject *kwargs)
{
    Xine_Video_Port_PyObject *port;
    int result;

    if (!PyArg_ParseTuple(args, "O!", &Xine_Video_Port_PyObject_Type, &port))
        return NULL;

    Py_BEGIN_ALLOW_THREADS
    result = xine_post_wire_video_port(self->post_out, port->vo);
    Py_END_ALLOW_THREADS
    _post_out_set_port(self);
    return PyBool_FromLong(result);
}

PyObject *
Xine_Post_Out_PyObject_wire_audio_port(Xine_Post_Out_PyObject *self, PyObject *args, PyObject *kwargs)
{
    Xine_Audio_Port_PyObject *port;
    int result;

    if (!PyArg_ParseTuple(args, "O!", &Xine_Audio_Port_PyObject_Type, &port))
        return NULL;

    Py_BEGIN_ALLOW_THREADS
    result = xine_post_wire_audio_port(self->post_out, port->ao);
    Py_END_ALLOW_THREADS
    _post_out_set_port(self);
    return PyBool_FromLong(result);
}

PyMethodDef Xine_Post_Out_PyObject_methods[] = {
    {"get_owner", (PyCFunction) Xine_Post_Out_PyObject_get_owner, METH_VARARGS},
    {"get_port", (PyCFunction) Xine_Post_Out_PyObject_get_port, METH_VARARGS},
    {"get_type", (PyCFunction) Xine_Post_Out_PyObject_get_type, METH_VARARGS},
    {"get_name", (PyCFunction) Xine_Post_Out_PyObject_get_name, METH_VARARGS},
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
    Py_TPFLAGS_DEFAULT | Py_TPFLAGS_BASETYPE,// | Py_TPFLAGS_HAVE_GC, /* tp_flags */
    "Xine Post Output Object",               /* tp_doc */
    0, //(traverseproc)Xine_Post_Out_PyObject__traverse,   /* tp_traverse */
    0, //(inquiry)Xine_Post_Out_PyObject__clear,           /* tp_clear */
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


