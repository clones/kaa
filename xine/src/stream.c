#include "xine.h"
#include "stream.h"
#include "structmember.h"
#include "post_out.h"

Xine_Stream_PyObject *
pyxine_new_stream_pyobject(Xine_PyObject *xine, xine_stream_t *stream,
                           Xine_Audio_Port_PyObject *ao, 
                           Xine_Video_Port_PyObject *vo, int owner)
{
    Xine_Stream_PyObject *o = (Xine_Stream_PyObject *)xine_object_to_pyobject_find(stream);
    if (o) {
        Py_INCREF(o);
        return o;
    }

    o = (Xine_Stream_PyObject *)Xine_Stream_PyObject__new(&Xine_Stream_PyObject_Type, NULL, NULL);
    if (!o)
        return NULL;
    o->stream = stream;
    o->xine_object_owner = owner;
    o->ao_pyobject = ao;
    Py_INCREF(ao);
    o->vo_pyobject = vo;
    Py_INCREF(vo);
    o->xine_pyobject = (PyObject *)xine;
    o->xine = xine->xine;
    Py_INCREF(xine);
    xine_object_to_pyobject_register(stream, (PyObject *)o);
    return o;
}




static int
Xine_Stream_PyObject__clear(Xine_Stream_PyObject *self)
{
    PyObject *tmp;
    if (self->xine_pyobject) {
        tmp = self->xine_pyobject;
        self->xine_pyobject = 0;
        Py_DECREF(tmp);
    }
    if (self->ao_pyobject) {
        tmp = (PyObject *)self->ao_pyobject;
        self->ao_pyobject = 0;
        Py_DECREF(tmp);
    }
    if (self->vo_pyobject) {
        tmp = (PyObject *)self->vo_pyobject;
        self->vo_pyobject = 0;
        Py_DECREF(tmp);
    }
    if (self->master) {
        tmp = (PyObject *)self->master;
        self->master= 0;
        Py_DECREF(tmp);
    }
    return 0;
}

static int
Xine_Stream_PyObject__traverse(Xine_Stream_PyObject *self, visitproc visit, void *arg)
{
    int ret;
    if (self->xine_pyobject) {
        ret = visit((PyObject *)self->xine_pyobject, arg);
        if (ret != 0)
            return ret;
    }
    if (self->ao_pyobject) {
        ret = visit((PyObject *)self->ao_pyobject, arg);
        if (ret != 0)
            return ret;
    }
    if (self->vo_pyobject) {
        ret = visit((PyObject *)self->vo_pyobject, arg);
        if (ret != 0)
            return ret;
    }
    if (self->master) {
        ret = visit((PyObject *)self->master, arg);
        if (ret != 0)
            return ret;
    }
    return 0;
}

PyObject *
Xine_Stream_PyObject__new(PyTypeObject *type, PyObject * args, PyObject * kwargs)
{
    Xine_Stream_PyObject *self;

    if (args) {
        PyErr_SetString(xine_error, "Don't call me directly");
        return NULL;
    }

    self = (Xine_Stream_PyObject *)type->tp_alloc(type, 0);
    self->stream = NULL;
    self->xine = NULL;
    self->xine_pyobject = NULL;
    self->wrapper = Py_None;
    Py_INCREF(Py_None);
    return (PyObject *)self;
}

static int
Xine_Stream_PyObject__init(Xine_Stream_PyObject *self, PyObject *args, PyObject *kwds)
{
    return 0;
}


static PyMemberDef Xine_Stream_PyObject_members[] = {
    {"wrapper", T_OBJECT_EX, offsetof(Xine_Stream_PyObject, wrapper), 0, "Wrapper object"},
    {NULL}
};


void
Xine_Stream_PyObject__dealloc(Xine_Stream_PyObject *self)
{
    printf("DEalloc Stream: %x\n", self->stream);
    if (self->stream && self->xine_object_owner) {
        Py_BEGIN_ALLOW_THREADS
        //xine_close(self->stream);
        xine_dispose(self->stream);
        Py_END_ALLOW_THREADS
    }
    Py_DECREF(self->wrapper);
    Xine_Stream_PyObject__clear(self);
    xine_object_to_pyobject_unregister(self->stream);
    self->ob_type->tp_free((PyObject*)self);
}

PyObject *
Xine_Stream_PyObject_open(Xine_Stream_PyObject *self, PyObject *args, PyObject *kwargs)
{
    char *mrl;
    int result;
    
    if (!PyArg_ParseTuple(args, "s", &mrl))
        return NULL;

    result = xine_open(self->stream, mrl);
    if (!result) {
        PyErr_Format(xine_error, "Failed to open stream (FIXME: add useful error).");
        return NULL;
    }

    return Py_INCREF(Py_None), Py_None;
}

PyObject *
Xine_Stream_PyObject_play(Xine_Stream_PyObject *self, PyObject *args, PyObject *kwargs)
{
    int pos = 0, time = 0, result;

    if (!PyArg_ParseTuple(args, "|ii", &pos, &time))
        return NULL;

    Py_BEGIN_ALLOW_THREADS
    result = xine_play(self->stream, pos, time);
    Py_END_ALLOW_THREADS
    if (!result) {
        PyErr_Format(xine_error, "Failed to play stream (FIXME: add useful error).");
        return NULL;
    }
    
    return Py_INCREF(Py_None), Py_None;
}

PyObject *
Xine_Stream_PyObject_stop(Xine_Stream_PyObject *self, PyObject *args, PyObject *kwargs)
{
    Py_BEGIN_ALLOW_THREADS
    xine_stop(self->stream);
    Py_END_ALLOW_THREADS
    return Py_INCREF(Py_None), Py_None;
}

PyObject *
Xine_Stream_PyObject_eject(Xine_Stream_PyObject *self, PyObject *args, PyObject *kwargs)
{
    int result;
    Py_BEGIN_ALLOW_THREADS
    result = xine_eject(self->stream);
    Py_END_ALLOW_THREADS
    return PyBool_FromLong(result);
}

PyObject *
Xine_Stream_PyObject_get_source(Xine_Stream_PyObject *self, PyObject *args, PyObject *kwargs)
{
    char *source;
    xine_post_out_t *output = NULL;

    if (!PyArg_ParseTuple(args, "s", &source))
        return NULL;

    if (!strcmp(source, "video"))
        output = xine_get_video_source(self->stream);
    else if (!strcmp(source, "audio"))
        output = xine_get_audio_source(self->stream);

    if (!output) {
        PyErr_Format(xine_error, "Failed to get output source for %s stream", source);
        return NULL;
    }

    return (PyObject *)pyxine_new_post_out_pyobject(NULL, output, 0);
}

PyObject *
Xine_Stream_PyObject_slave(Xine_Stream_PyObject *self, PyObject *args, PyObject *kwargs)
{
    PyObject *tmp = NULL;
    Xine_Stream_PyObject *slave;
    int affection, result;

    if (!PyArg_ParseTuple(args, "O!i", &Xine_Stream_PyObject_Type, &slave, &affection))
        return NULL;

    if (slave->master)
        tmp = slave->master;
    slave->master = (PyObject *)self;
    Py_INCREF(self);
    if (tmp)
        Py_DECREF(tmp);

    Py_BEGIN_ALLOW_THREADS
    result = xine_stream_master_slave(self->stream, slave->stream, affection);
    Py_END_ALLOW_THREADS
    return PyBool_FromLong(result);
}

PyObject *
Xine_Stream_PyObject_set_trick_mode(Xine_Stream_PyObject *self, PyObject *args, PyObject *kwargs)
{
    int mode, value, result;

    if (!PyArg_ParseTuple(args, "ii", &mode, &value))
        return NULL;

    result = xine_trick_mode(self->stream, mode, value);
    return PyBool_FromLong(result);
}

PyObject *
Xine_Stream_PyObject_get_current_vpts(Xine_Stream_PyObject *self, PyObject *args, PyObject *kwargs)
{
    return PyLong_FromLongLong(xine_get_current_vpts(self->stream));
}

PyObject *
Xine_Stream_PyObject_get_error(Xine_Stream_PyObject *self, PyObject *args, PyObject *kwargs)
{
    return PyLong_FromLongLong(xine_get_error(self->stream));
}

PyObject *
Xine_Stream_PyObject_get_status(Xine_Stream_PyObject *self, PyObject *args, PyObject *kwargs)
{
    return PyLong_FromLongLong(xine_get_status(self->stream));
}

PyObject *
Xine_Stream_PyObject_get_lang(Xine_Stream_PyObject *self, PyObject *args, PyObject *kwargs)
{
    int channel = -1, result;
    char lang[XINE_LANG_MAX+1], *type;

    if (!PyArg_ParseTuple(args, "si", &type, &channel))
        return NULL;

    if (!strcmp(type, "spu"))
        result = xine_get_spu_lang(self->stream, channel, &lang[0]);
    else
        result = xine_get_audio_lang(self->stream, channel, &lang[0]);
    
    if (!result) {
        Py_INCREF(Py_None);
        return Py_None;
    }

    return PyString_FromString(lang);
}


PyObject *
Xine_Stream_PyObject_get_pos_length(Xine_Stream_PyObject *self, PyObject *args, PyObject *kwargs)
{
    int pos_stream, pos_time, length_time, result;

    result = xine_get_pos_length(self->stream, &pos_stream, &pos_time, &length_time);
    if (!result)
        return Py_BuildValue("(sss)", NULL, NULL, NULL);

    return Py_BuildValue("(iii)", pos_stream, pos_time, length_time);
}


PyObject *
Xine_Stream_PyObject_get_info(Xine_Stream_PyObject *self, PyObject *args, PyObject *kwargs)
{
    int info;

    if (!PyArg_ParseTuple(args, "i", &info))
        return NULL;

    return PyLong_FromLong(xine_get_stream_info(self->stream, info));
}


PyObject *
Xine_Stream_PyObject_get_meta_info(Xine_Stream_PyObject *self, PyObject *args, PyObject *kwargs)
{
    int info;

    if (!PyArg_ParseTuple(args, "i", &info))
        return NULL;

    return Py_BuildValue("s", (xine_get_meta_info(self->stream, info)));
}


PyMethodDef Xine_Stream_PyObject_methods[] = {
    {"open", (PyCFunction) Xine_Stream_PyObject_open, METH_VARARGS },
    {"play", (PyCFunction) Xine_Stream_PyObject_play, METH_VARARGS },
    {"stop", (PyCFunction) Xine_Stream_PyObject_stop, METH_VARARGS },
    {"eject", (PyCFunction) Xine_Stream_PyObject_eject, METH_VARARGS },
    {"get_source", (PyCFunction) Xine_Stream_PyObject_get_source, METH_VARARGS },
    {"slave", (PyCFunction) Xine_Stream_PyObject_slave, METH_VARARGS },
    {"set_trick_mode", (PyCFunction) Xine_Stream_PyObject_set_trick_mode, METH_VARARGS },
    {"get_current_vpts", (PyCFunction) Xine_Stream_PyObject_get_current_vpts, METH_VARARGS },
    {"get_error", (PyCFunction) Xine_Stream_PyObject_get_error, METH_VARARGS },
    {"get_status", (PyCFunction) Xine_Stream_PyObject_get_status, METH_VARARGS },
    {"get_lang", (PyCFunction) Xine_Stream_PyObject_get_lang, METH_VARARGS },
    {"get_pos_length", (PyCFunction) Xine_Stream_PyObject_get_pos_length, METH_VARARGS },
    {"get_info", (PyCFunction) Xine_Stream_PyObject_get_info, METH_VARARGS },
    {"get_meta_info", (PyCFunction) Xine_Stream_PyObject_get_meta_info, METH_VARARGS },

    // TODO: xine_get_current_frame
    {NULL, NULL}
};

PyTypeObject Xine_Stream_PyObject_Type = {
    PyObject_HEAD_INIT(NULL) 
    0,                          /* ob_size */
    "_xine.Stream",               /* tp_name */
    sizeof(Xine_Stream_PyObject),      /* tp_basicsize */
    0,                          /* tp_itemsize */
    (destructor) Xine_Stream_PyObject__dealloc,        /* tp_dealloc */
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
    "Xine Stream Object",               /* tp_doc */
    (traverseproc)Xine_Stream_PyObject__traverse,   /* tp_traverse */
    (inquiry)Xine_Stream_PyObject__clear,           /* tp_clear */
    0,                         /* tp_richcompare */
    0,                         /* tp_weaklistoffset */
    0,                         /* tp_iter */
    0,                         /* tp_iternext */
    Xine_Stream_PyObject_methods,     /* tp_methods */
    Xine_Stream_PyObject_members,     /* tp_members */
    0,                         /* tp_getset */
    0,                         /* tp_base */
    0,                         /* tp_dict */
    0,                         /* tp_descr_get */
    0,                         /* tp_descr_set */
    0,                         /* tp_dictoffset */
    (initproc)Xine_Stream_PyObject__init, /* tp_init */
    0,                         /* tp_alloc */
    Xine_Stream_PyObject__new,        /* tp_new */
};


