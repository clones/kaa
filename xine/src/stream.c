#include "xine.h"
#include "stream.h"
#include "structmember.h"
#include "post_out.h"
#include "event_queue.h"

// Owner must be a Xine object
Xine_Stream_PyObject *
pyxine_new_stream_pyobject(Xine_PyObject *xine, xine_stream_t *stream, int do_dispose)
{
    xine_post_out_t *post_out;
    Xine_Stream_PyObject *o = (Xine_Stream_PyObject *)xine_object_to_pyobject_find(stream);
    if (o) {
        Py_INCREF(o);
        return o;
    }

    o = (Xine_Stream_PyObject *)Xine_Stream_PyObject__new(&Xine_Stream_PyObject_Type, NULL, NULL);
    if (!o)
        return NULL;

    o->stream = stream;
    o->do_dispose = do_dispose;
    o->xine = xine;
    Py_INCREF(o->xine);
 
    xine_object_to_pyobject_register(stream, (PyObject *)o);

    post_out = xine_get_video_source(stream);
    o->video_source = (PyObject *)pyxine_new_post_out_pyobject(xine, stream, post_out, 0);
    post_out = xine_get_audio_source(stream);
    o->audio_source = (PyObject *)pyxine_new_post_out_pyobject(xine, stream, post_out, 0);
 
    return o;
}



/*
static int
Xine_Stream_PyObject__clear(Xine_Stream_PyObject *self)
{
    PyObject **list[] = { &self->video_source, &self->audio_source, //&self->vo,
                          &self->owner_pyobject, &self->master, NULL};

    printf("STREAM: clear\n");
    return pyxine_gc_helper_clear(list);
}

static int
Xine_Stream_PyObject__traverse(Xine_Stream_PyObject *self, visitproc visit, void *arg)
{
    PyObject **list[] = { &self->video_source, &self->audio_source, &self->vo, &self->ao,
                          &self->owner_pyobject, &self->master, NULL};
    printf("STREAM: traverse\n");
    return pyxine_gc_helper_traverse(list, visit, arg);
}
*/

PyObject *
Xine_Stream_PyObject__new(PyTypeObject *type, PyObject * args, PyObject * kwargs)
{
    Xine_Stream_PyObject *self;

    if (args) {
        PyErr_SetString(xine_error, "Don't call me directly");
        return NULL;
    }

    self = (Xine_Stream_PyObject *)type->tp_alloc(type, 0);
    self->xine = NULL;

    self->master = self->wrapper = Py_None;
    Py_INCREF(Py_None);
    Py_INCREF(Py_None);

    return (PyObject *)self;
}

static int
Xine_Stream_PyObject__init(Xine_Stream_PyObject *self, PyObject *args, PyObject *kwds)
{
    return 0;
}


static PyMemberDef Xine_Stream_PyObject_members[] = {
    {"video_source", T_OBJECT_EX, offsetof(Xine_Stream_PyObject, video_source), 0, "Video source PostOut"},
    {"audio_source", T_OBJECT_EX, offsetof(Xine_Stream_PyObject, audio_source), 0, "Audio source PostOut"},
    {"wrapper", T_OBJECT_EX, offsetof(Xine_Stream_PyObject, wrapper), 0, "Wrapper object"},
    {NULL}
};


void
Xine_Stream_PyObject__dealloc(Xine_Stream_PyObject *self)
{
    printf("DEalloc Stream: %p\n", self->stream);
    if (self->stream && self->do_dispose) {
        printf("DISPOSE STREAM\n");
        self->do_dispose = 0;
        Py_BEGIN_ALLOW_THREADS
        xine_dispose(self->stream);
        Py_END_ALLOW_THREADS
    }
    printf("STREAM: DISPOSED: video source=%p audio_source=%p\n", self->video_source, self->audio_source);

    Py_DECREF(self->wrapper);
    Py_DECREF(self->video_source);
    Py_DECREF(self->audio_source);
    Py_DECREF(self->master);
    Py_DECREF(self->xine);

    //Xine_Stream_PyObject__clear(self);
    
    xine_object_to_pyobject_unregister(self->stream);
    self->ob_type->tp_free((PyObject*)self);
    printf("STREAM FREED\n");
}

PyObject *
Xine_Stream_PyObject_get_owner(Xine_Stream_PyObject *self, PyObject *args, PyObject *kwargs)
{
    Py_INCREF(self->xine);
    return (PyObject *)self->xine;
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
        PyErr_Format(xine_error, "Failed to open stream '%s' (FIXME: add useful error).", mrl);
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
Xine_Stream_PyObject_close(Xine_Stream_PyObject *self, PyObject *args, PyObject *kwargs)
{
    Py_BEGIN_ALLOW_THREADS
    xine_close(self->stream);
    Py_END_ALLOW_THREADS
    return Py_INCREF(Py_None), Py_None;
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
    if (tmp) {
        Py_DECREF(tmp);
    }

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
    return PyInt_FromLong(xine_get_error(self->stream));
}

PyObject *
Xine_Stream_PyObject_get_status(Xine_Stream_PyObject *self, PyObject *args, PyObject *kwargs)
{
    return PyInt_FromLong(xine_get_status(self->stream));
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

    return PyInt_FromLong(xine_get_stream_info(self->stream, info));
}


PyObject *
Xine_Stream_PyObject_get_meta_info(Xine_Stream_PyObject *self, PyObject *args, PyObject *kwargs)
{
    int info;
    const char *value;

    if (!PyArg_ParseTuple(args, "i", &info))
        return NULL;

    Py_BEGIN_ALLOW_THREADS
    value = xine_get_meta_info(self->stream, info);
    Py_END_ALLOW_THREADS
    return Py_BuildValue("s", value);
}

PyObject *
Xine_Stream_PyObject_get_param(Xine_Stream_PyObject *self, PyObject *args, PyObject *kwargs)
{
    int param, value;

    if (!PyArg_ParseTuple(args, "i", &param))
        return NULL;

    Py_BEGIN_ALLOW_THREADS
    value = xine_get_param(self->stream, param);
    Py_END_ALLOW_THREADS
    return PyInt_FromLong(value);
}

PyObject *
Xine_Stream_PyObject_set_param(Xine_Stream_PyObject *self, PyObject *args, PyObject *kwargs)
{
    int param, value;

    if (!PyArg_ParseTuple(args, "ii", &param, &value))
        return NULL;

    Py_BEGIN_ALLOW_THREADS
    xine_set_param(self->stream, param, value);
    Py_END_ALLOW_THREADS
    Py_INCREF(Py_None);
    return Py_None;
}

PyObject *
Xine_Stream_PyObject_new_event_queue(Xine_Stream_PyObject *self, PyObject *args, PyObject *kwargs)
{
    xine_event_queue_t *queue;

    queue = xine_event_new_queue(self->stream);
    return (PyObject *)pyxine_new_event_queue_pyobject(self->xine, self->stream, queue, 1);
}

PyObject *
Xine_Stream_PyObject_send_event(Xine_Stream_PyObject *self, PyObject *args, PyObject *kwargs)
{
    xine_event_t ev;
    int type;
    
    if (!PyArg_ParseTuple(args, "i", &type))
        return NULL;

    ev.type = type;
    ev.stream = self->stream;
    // TODO: interpret kwargs for data
    ev.data = 0;
    ev.data_length = 0;

    xine_event_send(self->stream, &ev);
    Py_INCREF(Py_None);
    return Py_None;
}

PyMethodDef Xine_Stream_PyObject_methods[] = {
    {"get_owner", (PyCFunction) Xine_Stream_PyObject_get_owner, METH_VARARGS },
    {"open", (PyCFunction) Xine_Stream_PyObject_open, METH_VARARGS },
    {"play", (PyCFunction) Xine_Stream_PyObject_play, METH_VARARGS },
    {"stop", (PyCFunction) Xine_Stream_PyObject_stop, METH_VARARGS },
    {"eject", (PyCFunction) Xine_Stream_PyObject_eject, METH_VARARGS },
    {"close", (PyCFunction) Xine_Stream_PyObject_close, METH_VARARGS },
    {"slave", (PyCFunction) Xine_Stream_PyObject_slave, METH_VARARGS },
    {"set_trick_mode", (PyCFunction) Xine_Stream_PyObject_set_trick_mode, METH_VARARGS },
    {"get_current_vpts", (PyCFunction) Xine_Stream_PyObject_get_current_vpts, METH_VARARGS },
    {"get_error", (PyCFunction) Xine_Stream_PyObject_get_error, METH_VARARGS },
    {"get_status", (PyCFunction) Xine_Stream_PyObject_get_status, METH_VARARGS },
    {"get_lang", (PyCFunction) Xine_Stream_PyObject_get_lang, METH_VARARGS },
    {"get_pos_length", (PyCFunction) Xine_Stream_PyObject_get_pos_length, METH_VARARGS },
    {"get_info", (PyCFunction) Xine_Stream_PyObject_get_info, METH_VARARGS },
    {"get_meta_info", (PyCFunction) Xine_Stream_PyObject_get_meta_info, METH_VARARGS },
    {"get_param", (PyCFunction) Xine_Stream_PyObject_get_param, METH_VARARGS },
    {"set_param", (PyCFunction) Xine_Stream_PyObject_set_param, METH_VARARGS },
    {"new_event_queue", (PyCFunction) Xine_Stream_PyObject_new_event_queue, METH_VARARGS },
    {"send_event", (PyCFunction) Xine_Stream_PyObject_send_event, METH_VARARGS | METH_KEYWORDS },

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
    Py_TPFLAGS_DEFAULT | Py_TPFLAGS_BASETYPE, // | Py_TPFLAGS_HAVE_GC, /* tp_flags */
    "Xine Stream Object",               /* tp_doc */
    0, //(traverseproc)Xine_Stream_PyObject__traverse,   /* tp_traverse */
    0, //(inquiry)Xine_Stream_PyObject__clear,           /* tp_clear */
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


