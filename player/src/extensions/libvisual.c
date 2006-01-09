#include <Python.h>
#include "structmember.h"
#include <libvisual/libvisual.h>
#include <stdlib.h>

typedef struct {
    PyObject_HEAD
    VisBin *bin;
    VisVideo *video;

    char *buffer;
    PyObject *pybuffer;
    int width, height, buffer_owned;
    int16_t pcmdata[2][512];
} Libvisual_PyObject;

#define Libvisual_PyObject_Check(v) ((v)->ob_type == &Libvisual_PyObject_Type)
extern PyTypeObject Libvisual_PyObject_Type;


static int 
vis_upload_callback(VisInput *input, VisAudio *audio, void *data)
{
    Libvisual_PyObject *self = (Libvisual_PyObject *)data;
    int i = 0;

    printf("UPLOAD CB\n");
    for (i = 0; i < 512; i++) {
        memcpy(audio->plugpcm[0], self->pcmdata[0], sizeof(int16_t)*512);
        memcpy(audio->plugpcm[1], self->pcmdata[1], sizeof(int16_t)*512);
    }
    return 0;
}

PyObject *
Libvisual_PyObject__new(PyTypeObject *type, PyObject *args, PyObject * kwargs)
{
    Libvisual_PyObject *self;

    Py_BEGIN_ALLOW_THREADS

    if (!visual_is_initialized()) {
        visual_init(NULL, NULL);
    }
    visual_log_set_verboseness(VISUAL_LOG_VERBOSENESS_HIGH);

    self = (Libvisual_PyObject *)type->tp_alloc(type, 0);
    self->bin = visual_bin_new();
    visual_bin_set_supported_depth(self->bin, VISUAL_VIDEO_DEPTH_32BIT);
    visual_bin_set_depth(self->bin, VISUAL_VIDEO_DEPTH_32BIT);


    self->video = visual_video_new();
    visual_video_set_depth(self->video, VISUAL_VIDEO_DEPTH_32BIT);
    visual_bin_set_video(self->bin, self->video);

    visual_bin_switch_set_style (self->bin, VISUAL_SWITCH_STYLE_MORPH);
    visual_bin_switch_set_automatic (self->bin, TRUE);
    visual_bin_switch_set_mode (self->bin, VISUAL_MORPH_MODE_TIME);
    visual_bin_switch_set_time (self->bin, 4, 0);


    Py_END_ALLOW_THREADS

    return (PyObject *)self;
}

static int
Libvisual_PyObject__init(Libvisual_PyObject *self, PyObject *args, PyObject *kwds)
{
    return 0;
}

void
Libvisual_PyObject__dealloc(Libvisual_PyObject *self)
{
    if (self->buffer && self->buffer_owned)
        free(self->buffer);
    if (self->pybuffer) {
        Py_DECREF(self->pybuffer);
    }

    self->ob_type->tp_free((PyObject*)self);
}

PyObject *
Libvisual_PyObject__set_size(Libvisual_PyObject *self, PyObject *args, PyObject *kwargs)
{
    int w, h;

    if (!PyArg_ParseTuple(args, "ii", &w, &h))
        return NULL;

    if (self->width == w && self->height == h) {
        Py_INCREF(Py_None);
        return Py_None;
    }

    if (self->buffer && self->buffer_owned)
        free(self->buffer);
    self->buffer = malloc(w * h * 4);
    self->buffer_owned = 1;

    Py_BEGIN_ALLOW_THREADS
    visual_video_set_dimension(self->video, w, h);
    visual_video_set_buffer(self->video, self->buffer);
    visual_video_set_pitch(self->video, w * 4);
    Py_END_ALLOW_THREADS
    //visual_bin_realize(self->bin);
    //visual_bin_sync(self->bin, FALSE);
    self->width = w;
    self->height = h;

    Py_INCREF(Py_None);
    return Py_None;
}

PyObject *
Libvisual_PyObject__set_actor(Libvisual_PyObject *self, PyObject *args, PyObject *kwargs)
{
    char *actor;
    VisInput *input;

    if (!PyArg_ParseTuple(args, "s", &actor))
        return NULL;

    Py_BEGIN_ALLOW_THREADS
    visual_bin_connect_by_names(self->bin, actor, NULL);
    input = visual_bin_get_input (self->bin);
    printf("Visual input: %p\n", input);
    printf("Set callback: %d\n", visual_input_set_callback (input, vis_upload_callback, self));
    visual_bin_realize(self->bin);
    visual_bin_sync(self->bin, FALSE);
    Py_END_ALLOW_THREADS

    Py_INCREF(Py_None);
    return Py_None;
}

PyObject *
Libvisual_PyObject__set_buffer(Libvisual_PyObject *self, PyObject *args, PyObject *kwargs)
{
    PyObject *buffer;
    char *ptr = NULL;
    int len;

    if (!PyArg_ParseTuple(args, "O", &buffer))
        return NULL;

    if (PyNumber_Check(buffer)) {
        ptr = (char *)PyLong_AsLong(buffer);
    } else {
        if (PyObject_AsWriteBuffer(buffer, (void **)&ptr, &len) == -1)
            return NULL;

        if (len < self->width * self->height * 4) {
            PyErr_Format(PyExc_ValueError, "Buffer is not large enough.");
            return NULL;
        }
    } 
    if (!ptr) {
        PyErr_Format(PyExc_ValueError, "Argument must be writable buffer or pointer");
        return NULL;
    }

    if (self->buffer && self->buffer_owned)
        free(self->buffer);

    visual_video_set_buffer(self->video, ptr);

    self->buffer = ptr;
    self->pybuffer = buffer;
    Py_INCREF(buffer);
    self->buffer_owned = 0;

    Py_INCREF(Py_None);
    return Py_None;
}

PyObject *
Libvisual_PyObject__get_buffer(Libvisual_PyObject *self, PyObject *args, PyObject *kwargs)
{
    if (self->buffer)
        return PyBuffer_FromMemory(self->buffer, self->width * self->height * 4);
    else if (self->pybuffer) {
        if (PyNumber_Check(self->pybuffer)) {
            return PyBuffer_FromMemory((void *)PyLong_AsLong(self->pybuffer), self->width * self->height * 4);
        } else {
            Py_INCREF(self->pybuffer);
            return self->pybuffer;
        }
    }

    Py_INCREF(Py_None);
    return Py_None;
}

PyObject *
Libvisual_PyObject__get_buffer_as_ptr(Libvisual_PyObject *self, PyObject *args, PyObject *kwargs)
{
    if (self->buffer)
        return Py_BuildValue("l", (long)self->buffer);
    else if (self->pybuffer) {
        if (!PyNumber_Check(self->pybuffer)) {
            char *ptr = NULL;
            int len;
            if (PyObject_AsReadBuffer(self->pybuffer, (const void **)&ptr, &len) == -1)
                return NULL;
            return Py_BuildValue("l", (long)ptr);
        }
        else {
            Py_INCREF(self->pybuffer);
            return self->pybuffer;
        }
    }
    Py_INCREF(Py_None);
    return Py_None;
}

PyObject *
Libvisual_PyObject__upload_pcm_data(Libvisual_PyObject *self, PyObject *args, PyObject *kwargs)
{
    PyObject *buffer;
    char *ptr = NULL;
    int len, required = 512 * sizeof(int16_t) * 2;

    if (!PyArg_ParseTuple(args, "O", &buffer))
        return NULL;
    if (PyObject_AsReadBuffer(buffer, (const void **)&ptr, &len) == -1)
        return NULL;
    if (len < required) {
        PyErr_Format(PyExc_ValueError, "PCM buffer is too short (must be %d bytes)", required);
    }
    memcpy(self->pcmdata, ptr, required);

    Py_INCREF(Py_None);
    return Py_None;
}


PyObject *
Libvisual_PyObject__update(Libvisual_PyObject *self, PyObject *args, PyObject *kwargs)
{
    int i;
    for (i=0;i<10;i++) printf("%x ", (uint8_t)self->buffer[640*4*200+100+i]); printf("\n");
    Py_BEGIN_ALLOW_THREADS
    visual_bin_run(self->bin);
    Py_END_ALLOW_THREADS

    Py_INCREF(Py_None);
    return Py_None;
}

PyMethodDef Libvisual_PyObject_methods[] = {
    {"set_size", (PyCFunction) Libvisual_PyObject__set_size, METH_VARARGS },
    {"set_actor", (PyCFunction) Libvisual_PyObject__set_actor, METH_VARARGS },
    {"set_buffer", (PyCFunction) Libvisual_PyObject__set_buffer, METH_VARARGS },
    {"get_buffer", (PyCFunction) Libvisual_PyObject__get_buffer, METH_VARARGS },
    {"get_buffer_as_ptr", (PyCFunction) Libvisual_PyObject__get_buffer_as_ptr, METH_VARARGS },
    {"upload_pcm_data", (PyCFunction) Libvisual_PyObject__upload_pcm_data, METH_VARARGS },
    {"update", (PyCFunction) Libvisual_PyObject__update, METH_VARARGS },
    {NULL, NULL}
};

static PyMemberDef Libvisual_PyObject_members[] = {
    {NULL}
};

PyTypeObject Libvisual_PyObject_Type = {
    PyObject_HEAD_INIT(NULL)
    0,                          /* ob_size */
    "_libvisual.Libvisual",               /* tp_name */
    sizeof(Libvisual_PyObject),      /* tp_basicsize */
    0,                          /* tp_itemsize */
    (destructor) Libvisual_PyObject__dealloc,        /* tp_dealloc */
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
    "Xine Event Object",               /* tp_doc */
    0, //(traverseproc)Libvisual_PyObject__traverse,   /* tp_traverse */
    0, //(inquiry)Libvisual_PyObject__clear,           /* tp_clear */
    0,                         /* tp_richcompare */
    0,                         /* tp_weaklistoffset */
    0,                         /* tp_iter */
    0,                         /* tp_iternext */
    Libvisual_PyObject_methods,     /* tp_methods */
    Libvisual_PyObject_members,     /* tp_members */
    0,                         /* tp_getset */
    0,                         /* tp_base */
    0,                         /* tp_dict */
    0,                         /* tp_descr_get */
    0,                         /* tp_descr_set */
    0,                         /* tp_dictoffset */
    (initproc)Libvisual_PyObject__init, /* tp_init */
    0,                         /* tp_alloc */
    Libvisual_PyObject__new,        /* tp_new */
};

PyMethodDef libvisual_methods[] = {
    { NULL }
};

void init_libvisual()
{
    PyObject *m;

    m =  Py_InitModule("_libvisual", libvisual_methods);
    if (PyType_Ready(&Libvisual_PyObject_Type) < 0)
        return;
    Py_INCREF(&Libvisual_PyObject_Type);
    PyModule_AddObject(m, "Libvisual", (PyObject *)&Libvisual_PyObject_Type);
}

