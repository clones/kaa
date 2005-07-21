#include "xine.h"
#include "structmember.h"
#include "drivers/x11.h"
#include "video_port.h"
#include "audio_port.h"
#include "stream.h"
#include "post.h"
#include "post_out.h"
#include "post_in.h"
#include "post/buffer.h"

PyObject *xine_error;
// Maps xine object actresses to Xine python objects
static PyObject *xine_object_to_pyobject_dict = 0;


///

void
xine_object_to_pyobject_register(void *ptr, PyObject *o)
{
    PyObject *key = PyLong_FromLong((long)ptr), *val;
    if (!PyDict_Contains(xine_object_to_pyobject_dict, key)) {
        val = PyCObject_FromVoidPtr(o, NULL);
        PyDict_SetItem(xine_object_to_pyobject_dict, key, val);
        Py_DECREF(val);
    }
    Py_DECREF(key);
}

void
xine_object_to_pyobject_unregister(void *ptr)
{
    PyObject *key = PyLong_FromLong((long)ptr);
    if (PyDict_Contains(xine_object_to_pyobject_dict, key)) {
        PyDict_DelItem(xine_object_to_pyobject_dict, key);
    }
    Py_DECREF(key);
}

PyObject *
xine_object_to_pyobject_find(void *ptr)
{
    PyObject *key = PyLong_FromLong((long)ptr);
    PyObject *o = NULL;
    if (PyDict_Contains(xine_object_to_pyobject_dict, key)) {
        o = PyDict_GetItem(xine_object_to_pyobject_dict, key);
    }
    Py_DECREF(key);
    if (o)
        return (PyObject *)PyCObject_AsVoidPtr(o);
    return NULL;
}


// A version of the above function available in python space.
PyObject *
Xine_find_object_by_id(PyObject *self, PyObject *args, PyObject *kwargs)
{
    int id;
    PyObject *o;

    if (!PyArg_ParseTuple(args, "i", &id))
        return NULL;
    o = xine_object_to_pyobject_find((void *)id);
    if (!o) {
        Py_INCREF(Py_None);
        return Py_None;
    }
    return o;
}

//
// GC helper functions
int
pyxine_gc_helper_clear(PyObject ***list)
{
    int i;
    for (i = 0; list[i]; i++) {
        if (!*list[i])
            continue;
        PyObject *tmp = *list[i];
        *list[i] = 0;
        Py_DECREF(tmp);
    }
    return 0;
}

int
pyxine_gc_helper_traverse(PyObject ***list, visitproc visit, void *arg)
{
    int i, ret;
    for (i = 0; list[i]; i++) {
        if (!*list[i])
            continue;
        ret = visit(*list[i], arg);
        if (ret != 0)
            return ret;
    }
    return 0;
}

//


void
_xine_log_callback(void *xine_pyobject, int section)
{
    PyObject *args, *result;
    Xine_PyObject *xine = (Xine_PyObject *)xine_pyobject;

    if (xine->log_callback != Py_None) {
        args = Py_BuildValue("(i)", section);
        result = PyEval_CallObject(xine->log_callback, args);
        Py_DECREF(args);
        Py_DECREF(result);
    }
}


static int
Xine_PyObject__clear(Xine_PyObject *self)
{
    PyObject **list[] = {&self->dependencies, &self->log_callback, NULL};
    return pyxine_gc_helper_clear(list);
}

static int
Xine_PyObject__traverse(Xine_PyObject *self, visitproc visit, void *arg)
{
    PyObject **list[] = {&self->dependencies, &self->log_callback, NULL};
    return pyxine_gc_helper_traverse(list, visit, arg);
}

PyObject *
Xine_PyObject__new(PyTypeObject *type, PyObject * args, PyObject * kwargs)
{
    Xine_PyObject *self;

    self = (Xine_PyObject *)type->tp_alloc(type, 0);
    self->dependencies = PyList_New(0);
    self->wrapper = Py_None;
    self->log_callback = Py_None;
    Py_INCREF(Py_None);
    Py_INCREF(Py_None);
    return (PyObject *)self;
}

static int
Xine_PyObject__init(Xine_PyObject *self, PyObject *args, PyObject *kwds)
{
    char cfgfile[PATH_MAX];
    xine_t *xine;

    xine = xine_new();

    if (!xine) {
        PyErr_SetString(PyExc_RuntimeError, "Unknown error creating Xine object");
        return -1;
    }

    printf("Init Xine\n");

    snprintf(cfgfile, PATH_MAX, "%s%s", xine_get_homedir(), "/.xine/config");
    xine_config_load(xine, cfgfile);
    xine_init(xine);
    xine_register_plugins(xine, xine_buffer_plugin_info);
    self->xine = xine;
    xine_object_to_pyobject_register(xine, (PyObject *)self);

    // This isn't implemented in xine yet.
    //xine_register_log_cb(xine, _xine_log_callback, self);

    return 0;
}

static PyMemberDef Xine_PyObject_members[] = {
    {"dependencies", T_OBJECT_EX, offsetof(Xine_PyObject, dependencies), 0, "Dependencies"},
    {"wrapper", T_OBJECT_EX, offsetof(Xine_PyObject, wrapper), 0, "Wrapper object"},
    {"log_callback", T_OBJECT_EX, offsetof(Xine_PyObject, log_callback), 0, "Log Callback"},
    {NULL}
};


void
Xine_PyObject__dealloc(Xine_PyObject *self)
{
    printf("DEalloc Xine: %x\n", self->xine);
    if (self->xine) {
        xine_exit(self->xine);
    }
    Py_DECREF(self->wrapper);
    Xine_PyObject__clear(self);
    xine_object_to_pyobject_unregister(self->xine);
    self->ob_type->tp_free((PyObject*)self);
}


PyObject *
Xine_PyObject_list_plugins(Xine_PyObject *self, PyObject *args, PyObject *kwargs)
{
    char *type;
    const char *const *list;
    PyObject *pylist = NULL;
    int i, post_types = -1;

    if (!PyArg_ParseTuple(args, "s|i", &type, &post_types))
        return NULL;
    if (!strcmp(type, "video"))
        list = xine_list_video_output_plugins(self->xine);
    else if (!strcmp(type, "audio"))
        list = xine_list_audio_output_plugins(self->xine);
    else if (!strcmp(type, "demuxer"))
        list = xine_list_demuxer_plugins(self->xine);
    else if (!strcmp(type, "input"))
        list = xine_list_input_plugins(self->xine);
    else if (!strcmp(type, "spu"))
        list = xine_list_spu_plugins(self->xine);
    else if (!strcmp(type, "audio_decoder"))
        list = xine_list_audio_decoder_plugins(self->xine);
    else if (!strcmp(type, "video_decoder"))
        list = xine_list_video_decoder_plugins(self->xine);
    else if (!strcmp(type, "post")) {
        if (post_types == -1)
            list = xine_list_post_plugins(self->xine);
        else
            list = xine_list_post_plugins_typed(self->xine, post_types);
    }
    else {
        PyErr_Format(xine_error, "Unknown plugin type: %s", type);
        return NULL;
    }

    pylist = PyList_New(0);
    for (i = 0; list[i] != 0; i++) {
        PyObject *str = PyString_FromString(list[i]);
        PyList_Append(pylist, str);
        Py_DECREF(str);
    }
    return pylist;
}

PyObject *
Xine_PyObject_open_video_driver(Xine_PyObject *self, PyObject *args, PyObject *kwargs)
{
    xine_video_port_t *vo_port = NULL;
    Xine_Video_Port_PyObject *vo;
    char *driver;
    void *finalize_data = NULL;

    if (!PyArg_ParseTuple(args, "s", &driver))
        return NULL;

    if (!strcmp(driver, "xv") || !strcmp(driver, "xshm") || !strcmp(driver, "auto")) {
        vo_port = x11_open_video_driver(self, driver, kwargs, &finalize_data);
    } else if (!strcmp(driver, "none")) {
        vo_port = xine_open_video_driver(self->xine, driver, XINE_VISUAL_TYPE_NONE, 0);
    }
        
    if (!vo_port && !PyErr_Occurred()) {
        PyErr_Format(xine_error, "Failed to open driver: %s", driver);
        return NULL;
    }

    vo = pyxine_new_video_port_pyobject((PyObject *)self, vo_port, 1);

    if (!strcmp(driver, "xv") || !strcmp(driver, "auto") || !strcmp(driver, "xshm")) {
        x11_open_video_driver_finalize(vo, finalize_data);
    }
    return (PyObject *)vo;
}

PyObject *
Xine_PyObject_open_audio_driver(Xine_PyObject *self, PyObject *args, PyObject *kwargs)
{
    char *driver;
    Xine_Audio_Port_PyObject *o;
    xine_audio_port_t *ao_port;

    if (!PyArg_ParseTuple(args, "s", &driver))
        return NULL;


    ao_port = xine_open_audio_driver(self->xine, driver, NULL);

    if (!ao_port) {
        PyErr_Format(xine_error, "Failed to open audio driver.");
        return NULL;
    }

    return (PyObject *)pyxine_new_audio_port_pyobject((PyObject *)self, ao_port, 1);
}

PyObject *
Xine_PyObject_stream_new(Xine_PyObject *self, PyObject *args, PyObject *kwargs)
{
    Xine_Audio_Port_PyObject *ao;
    Xine_Video_Port_PyObject *vo;
    Xine_Stream_PyObject *o;
    xine_stream_t *stream;

    if (!PyArg_ParseTuple(args, "O!O!", &Xine_Audio_Port_PyObject_Type, &ao,
                                        &Xine_Video_Port_PyObject_Type, &vo))
        return NULL;

    
    stream = xine_stream_new(self->xine, ao->ao, vo->vo);
    if (!stream) {
        PyErr_Format(xine_error, "Failed to create stream.");
        return NULL;
    }
    return (PyObject *)pyxine_new_stream_pyobject((PyObject *)self, stream, 1);
}

PyObject *
Xine_PyObject_post_init(Xine_PyObject *self, PyObject *args, PyObject *kwargs)
{
    char *name;
    int inputs, i;
    PyObject *audio_targets, *video_targets, *post_pyobject;
    xine_video_port_t **vo;
    xine_audio_port_t **ao;
    xine_post_t *post;

    if (!PyArg_ParseTuple(args, "siOO", &name, &inputs, &audio_targets,
                          &video_targets))
        return NULL;

    ao = (xine_audio_port_t **)malloc((1 + sizeof(xine_audio_port_t *) * PyList_Size(audio_targets)));
    for (i = 0; i < PyList_Size(audio_targets); i++)
        ao[i] = ((Xine_Audio_Port_PyObject *)PyList_GetItem(audio_targets, i))->ao;
    ao[i] = NULL;

    vo = (xine_video_port_t **)malloc((1 + sizeof(xine_video_port_t *) * PyList_Size(video_targets)));
    for (i = 0; i < PyList_Size(video_targets); i++)
        vo[i] = ((Xine_Video_Port_PyObject *)PyList_GetItem(video_targets, i))->vo;
    vo[i] = NULL;
    
    post = xine_post_init(self->xine, name, inputs, ao, vo);

    if (post)
        post_pyobject = (PyObject *)pyxine_new_post_pyobject((PyObject *)self, post, name, 1);

    free(ao);
    free(vo);
    
    if (!post) {
        PyErr_Format(xine_error, "Failed to initialize post plugin.");
        return NULL;
    }
    return post_pyobject;


}


PyObject *
Xine_PyObject_get_log_names(Xine_PyObject *self, PyObject *args, PyObject *kwargs)
{
    const char *const *list;
    PyObject *pylist = NULL;
    int i;

    list = xine_get_log_names(self->xine);
    pylist = PyList_New(0);
    for (i = 0; list[i] != 0; i++) {
        PyObject *str = PyString_FromString(list[i]);
        PyList_Append(pylist, str);
        Py_DECREF(str);
    }
    return pylist;
}

PyObject *
Xine_PyObject_get_log(Xine_PyObject *self, PyObject *args, PyObject *kwargs)
{
    char *type;
    const char *const *list;
    PyObject *pylist = NULL;
    int i, section;

    if (!PyArg_ParseTuple(args, "i", &section))
        return NULL;
    list = xine_get_log(self->xine, section);
    pylist = PyList_New(0);
    for (i = 0; list && list[i] != 0; i++) {
        if (!list[i] || *list[i] == 0)
            continue;
        PyObject *str = PyString_FromString(list[i]);
        PyList_Append(pylist, str);
        Py_DECREF(str);
    }
    return pylist;
}

PyObject *
Xine_PyObject_set_engine_param(Xine_PyObject *self, PyObject *args, PyObject *kwargs)
{
    int param, value;

    if (!PyArg_ParseTuple(args, "ii", &param, &value))
        return NULL;
    xine_engine_set_param(self->xine, param, value);
    return Py_INCREF(Py_None), Py_None;
}

PyObject *
Xine_PyObject_get_engine_param(Xine_PyObject *self, PyObject *args, PyObject *kwargs)
{
    int param, value;

    if (!PyArg_ParseTuple(args, "i", &param))
        return NULL;
    value = xine_engine_get_param(self->xine, param);
    return PyInt_FromLong(value);
}

PyObject *
Xine_PyObject_get_input_plugin_ids(Xine_PyObject *self, PyObject *args, PyObject *kwargs)
{
    const char *const *list;
    PyObject *pylist = NULL;
    int i;
    char *type;

    if (!PyArg_ParseTuple(args, "s", &type))
        return NULL;
    if (!strcmp(type, "browsable"))
        list = xine_get_browsable_input_plugin_ids(self->xine);
    else
        list = xine_get_autoplay_input_plugin_ids(self->xine);

    pylist = PyList_New(0);
    for (i = 0; list && list[i] != 0; i++) {
        PyObject *str = PyString_FromString(list[i]);
        PyList_Append(pylist, str);
        Py_DECREF(str);
    }
    return pylist;
}

PyObject *
Xine_PyObject_get_browse_mrls(Xine_PyObject *self, PyObject *args, PyObject *kwargs)
{
    xine_mrl_t **mrls;
    PyObject *pylist = NULL, *dict, *val;
    char *plugin_id, *start_mrl;
    int i, num;

    if (!PyArg_ParseTuple(args, "sz", &plugin_id, &start_mrl))
        return NULL;
    mrls = xine_get_browse_mrls(self->xine, plugin_id, start_mrl, &num);
    if (!mrls) {
        PyErr_Format(xine_error, "Failed to get browse mrls -- unknown plugin?");
        return NULL;
    }

    pylist = PyList_New(0);
    for (i = 0; i < num; i++) {
        dict = PyDict_New();
        val = Py_BuildValue("s", mrls[i]->origin);
        PyDict_SetItemString(dict, "origin", val);
        Py_DECREF(val);

        val = Py_BuildValue("s", mrls[i]->link);
        PyDict_SetItemString(dict, "link", val);
        Py_DECREF(val);

        val = Py_BuildValue("s", mrls[i]->mrl);
        PyDict_SetItemString(dict, "mrl", val);
        Py_DECREF(val);

        val = Py_BuildValue("i", mrls[i]->type);
        PyDict_SetItemString(dict, "type", val);
        Py_DECREF(val);

        val = Py_BuildValue("i", mrls[i]->size);
        PyDict_SetItemString(dict, "size", val);
        Py_DECREF(val);

        PyList_Append(pylist, dict);
        Py_DECREF(dict);
    }
    return pylist;
}


PyObject *
Xine_PyObject_get_autoplay_mrls(Xine_PyObject *self, PyObject *args, PyObject *kwargs)
{
    PyObject *pylist = NULL;
    int i, num;
    char *plugin, **mrls;

    if (!PyArg_ParseTuple(args, "s", &plugin))
        return NULL;

    mrls = xine_get_autoplay_mrls(self->xine, plugin, &num);
    if (!mrls) {
        PyErr_Format(xine_error, "Failed to get autoplay mrls -- unknown plugin?");
        return NULL;
    }

    pylist = PyList_New(0);
    for (i = 0; i < num; i++) {
        PyObject *str = PyString_FromString(mrls[i]);
        PyList_Append(pylist, str);
        Py_DECREF(str);
    }
    return pylist;
}


PyObject *
Xine_PyObject_get_file_extensions(Xine_PyObject *self, PyObject *args, PyObject *kwargs)
{
    PyObject *o;
    char *s = xine_get_file_extensions(self->xine);
    o = Py_BuildValue("z", s);
    free(s);
    return o;
}

PyObject *
Xine_PyObject_get_mime_types(Xine_PyObject *self, PyObject *args, PyObject *kwargs)
{
    PyObject *o;
    char *s = xine_get_mime_types(self->xine);
    o = Py_BuildValue("z", s);
    free(s);
    return o;
}

PyMethodDef Xine_PyObject_methods[] = {
    {"list_plugins", (PyCFunction) Xine_PyObject_list_plugins, METH_VARARGS },
    {"open_video_driver", (PyCFunction) Xine_PyObject_open_video_driver, METH_VARARGS | METH_KEYWORDS},
    {"open_audio_driver", (PyCFunction) Xine_PyObject_open_audio_driver, METH_VARARGS | METH_KEYWORDS},
    {"stream_new", (PyCFunction) Xine_PyObject_stream_new, METH_VARARGS },
    {"post_init", (PyCFunction) Xine_PyObject_post_init, METH_VARARGS },
    {"get_log_names", (PyCFunction) Xine_PyObject_get_log_names, METH_VARARGS },
    {"get_log", (PyCFunction) Xine_PyObject_get_log, METH_VARARGS },
    {"get_engine_param", (PyCFunction) Xine_PyObject_get_engine_param, METH_VARARGS },
    {"set_engine_param", (PyCFunction) Xine_PyObject_set_engine_param, METH_VARARGS },
    {"get_input_plugin_ids", (PyCFunction) Xine_PyObject_get_input_plugin_ids, METH_VARARGS },
    {"get_browse_mrls", (PyCFunction) Xine_PyObject_get_browse_mrls, METH_VARARGS },
    {"get_autoplay_mrls", (PyCFunction) Xine_PyObject_get_autoplay_mrls, METH_VARARGS },
    {"get_file_extensions", (PyCFunction) Xine_PyObject_get_file_extensions, METH_VARARGS },
    {"get_mime_types", (PyCFunction) Xine_PyObject_get_mime_types, METH_VARARGS },
    {NULL, NULL}
};

int
Xine_PyObject__compare(Xine_PyObject *a, Xine_PyObject *b)
{
    return (a->xine == b->xine) ? 0 : 1;
}


PyTypeObject Xine_PyObject_Type = {
    PyObject_HEAD_INIT(NULL) 
    0,                          /* ob_size */
    "_xine.Xine",               /* tp_name */
    sizeof(Xine_PyObject),      /* tp_basicsize */
    0,                          /* tp_itemsize */
    (destructor) Xine_PyObject__dealloc,        /* tp_dealloc */
    0,                          /* tp_print */
    0,                          /* tp_getattr */
    0,                          /* tp_setattr */
    (cmpfunc) Xine_PyObject__compare, /* tp_compare */
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
    "Xine Object",               /* tp_doc */
    (traverseproc)Xine_PyObject__traverse,   /* tp_traverse */
    (inquiry)Xine_PyObject__clear,           /* tp_clear */
    0,                         /* tp_richcompare */
    0,                         /* tp_weaklistoffset */
    0,                         /* tp_iter */
    0,                         /* tp_iternext */
    Xine_PyObject_methods,     /* tp_methods */
    Xine_PyObject_members,     /* tp_members */
    0,                         /* tp_getset */
    0,                         /* tp_base */
    0,                         /* tp_dict */
    0,                         /* tp_descr_get */
    0,                         /* tp_descr_set */
    0,                         /* tp_dictoffset */
    (initproc)Xine_PyObject__init, /* tp_init */
    0,                         /* tp_alloc */
    Xine_PyObject__new,        /* tp_new */
};


PyObject *
Xine_get_version(PyObject *module, PyObject *args, PyObject *kwargs)
{
    return PyString_FromString(xine_get_version_string());
}

PyMethodDef xine_methods[] = {
    {"find_object_by_id", (PyCFunction) Xine_find_object_by_id, METH_VARARGS },
    {"get_version", (PyCFunction) Xine_get_version, METH_VARARGS },
    {NULL}
};


void **get_module_api(char *module)
{
    PyObject *m, *c_api;
    void **ptrs;

    m = PyImport_ImportModule(module);
    if (m == NULL)
       return;
    c_api = PyObject_GetAttrString(m, "_C_API");
    if (c_api == NULL || !PyCObject_Check(c_api))
        return;
    ptrs = (void **)PyCObject_AsVoidPtr(c_api);
    Py_DECREF(c_api);
    return ptrs;
}



void
init_xine()
{
    PyObject *m, *c_api;
    void **display_api_ptrs;

    m = Py_InitModule("_xine", xine_methods);
    xine_error = PyErr_NewException("xine.XineError", NULL, NULL);
    Py_INCREF(xine_error);
    PyModule_AddObject(m, "XineError", xine_error);

    if (PyType_Ready(&Xine_PyObject_Type) < 0)
        return;
    Py_INCREF(&Xine_PyObject_Type);
    PyModule_AddObject(m, "Xine", (PyObject *)&Xine_PyObject_Type);

    if (PyType_Ready(&Xine_Video_Port_PyObject_Type) < 0)
        return;
    Py_INCREF(&Xine_Video_Port_PyObject_Type);
    PyModule_AddObject(m, "VideoPort", (PyObject *)&Xine_Video_Port_PyObject_Type);

    if (PyType_Ready(&Xine_Audio_Port_PyObject_Type) < 0)
        return;
    Py_INCREF(&Xine_Audio_Port_PyObject_Type);
    PyModule_AddObject(m, "AudioPort", (PyObject *)&Xine_Audio_Port_PyObject_Type);
    
    if (PyType_Ready(&Xine_Stream_PyObject_Type) < 0)
        return;
    Py_INCREF(&Xine_Stream_PyObject_Type);
    PyModule_AddObject(m, "Stream", (PyObject *)&Xine_Stream_PyObject_Type);

    if (PyType_Ready(&Xine_Post_PyObject_Type) < 0)
        return;
    Py_INCREF(&Xine_Post_PyObject_Type);
    PyModule_AddObject(m, "Post", (PyObject *)&Xine_Post_PyObject_Type);

    if (PyType_Ready(&Xine_Post_Out_PyObject_Type) < 0)
        return;
    Py_INCREF(&Xine_Post_Out_PyObject_Type);
    PyModule_AddObject(m, "PostOut", (PyObject *)&Xine_Post_Out_PyObject_Type);

    if (PyType_Ready(&Xine_Post_In_PyObject_Type) < 0)
        return;
    Py_INCREF(&Xine_Post_In_PyObject_Type);
    PyModule_AddObject(m, "PostIn", (PyObject *)&Xine_Post_In_PyObject_Type);

    if (xine_object_to_pyobject_dict == NULL)
        xine_object_to_pyobject_dict = PyDict_New();

#if 1
    display_api_ptrs = get_module_api("kaa.display._Display");
    if (display_api_ptrs == NULL) {
        PyErr_Format(xine_error, "Failed to import kaa.display");
        return;
    }
    X11Window_PyObject_Type = display_api_ptrs[1];
    x11window_object_decompose = display_api_ptrs[2];
#else
    X11Window_PyObject_Type = NULL;
#endif

    PyEval_InitThreads();
}
