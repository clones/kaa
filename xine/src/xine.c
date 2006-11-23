#include "xine.h"
#include "structmember.h"
#include "vo_driver.h"
#include "video_port.h"
#include "audio_port.h"
#include "stream.h"
#include "post.h"
#include "post_out.h"
#include "post_in.h"
#include "event_queue.h"
#include "event.h"

#include "drivers/video_out_kaa.h"
#include "drivers/video_out_dummy.h"
#include "drivers/kaa.h"
#ifdef HAVE_X11
#include "drivers/x11.h"
#endif
#include "drivers/dummy.h"
#include "drivers/common.h"

PyObject *xine_error;
extern PyObject *xine_object_to_pyobject_dict;

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
    PyObject **list[] = {&self->log_callback, NULL};
    //printf("XINE CLEAR\n");
    return pyxine_gc_helper_clear(list);
}

static int
Xine_PyObject__traverse(Xine_PyObject *self, visitproc visit, void *arg)
{
    PyObject **list[] = {/*&self->dependencies, */&self->log_callback, NULL};
    //printf("XINE TRAV: %d\n", PySequence_Length(self->dependencies));
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

    snprintf(cfgfile, PATH_MAX, "%s%s", xine_get_homedir(), "/.xine/config");
    xine_config_load(xine, cfgfile);
    xine_init(xine);
    xine_register_plugins(xine, xine_vo_kaa_plugin_info);
    xine_register_plugins(xine, xine_vo_dummy_plugin_info);
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
    printf("DEalloc Xine: %p\n", self->xine);
    Py_DECREF(self->wrapper);
    Py_DECREF(self->dependencies);
    Xine_PyObject__clear(self);
    xine_object_to_pyobject_unregister(self->xine);

    printf("XINE EXIT\n");
    if (self->xine) {
        xine_exit(self->xine);
    }

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
Xine_PyObject_load_video_output_plugin(Xine_PyObject *self, PyObject *args, PyObject *kwargs)
{
    vo_driver_t *vo_driver = NULL;
    Xine_VO_Driver_PyObject *vo_driver_pyobject = NULL;
    char *driver;
    void *visual;
    int visual_type;
    driver_info_common *driver_info;

    if (!PyArg_ParseTuple(args, "s", &driver))
        return NULL;

    if (!driver_get_visual_info(self, driver, kwargs, &visual_type, &visual, &driver_info))
        return NULL;

    vo_driver = _x_load_video_output_plugin(self->xine, driver, visual_type, visual);
    if (!vo_driver) {
        PyErr_Format(xine_error, "Failed to open driver: %s", driver);
        return NULL;
    }
    if (visual)
        free(visual);
    if (driver_info)
        driver_info->driver = vo_driver;

    vo_driver_pyobject = pyxine_new_vo_driver_pyobject(self, self->xine, vo_driver, 1);
    vo_driver_pyobject->driver_info = driver_info;

    return (PyObject *)vo_driver_pyobject;
}

PyObject *
Xine_PyObject_open_audio_driver(Xine_PyObject *self, PyObject *args, PyObject *kwargs)
{
    char *driver;
    xine_audio_port_t *ao_port;

    if (!PyArg_ParseTuple(args, "s", &driver))
        return NULL;


    ao_port = xine_open_audio_driver(self->xine, driver, NULL);

    if (!ao_port) {
        PyErr_Format(xine_error, "Failed to open audio driver.");
        return NULL;
    }

    return (PyObject *)pyxine_new_audio_port_pyobject(self, self->xine, ao_port, 1);
}

PyObject *
Xine_PyObject_stream_new(Xine_PyObject *self, PyObject *args, PyObject *kwargs)
{
    Xine_Audio_Port_PyObject *ao;
    Xine_Video_Port_PyObject *vo;
    xine_stream_t *stream;
    PyObject *stream_pyobject;

    if (!PyArg_ParseTuple(args, "O!O!", &Xine_Audio_Port_PyObject_Type, &ao,
                                        &Xine_Video_Port_PyObject_Type, &vo))
        return NULL;

    
    stream = xine_stream_new(self->xine, ao->ao, vo->vo);
    if (!stream) {
        PyErr_Format(xine_error, "Failed to create stream.");
        return NULL;
    }

    stream_pyobject = (PyObject *)pyxine_new_stream_pyobject(self, stream, 1);
    return stream_pyobject;
}

PyObject *
Xine_PyObject_post_init(Xine_PyObject *self, PyObject *args, PyObject *kwargs)
{
    char *name;
    int inputs, i;
    PyObject *audio_targets, *video_targets, *post_pyobject = NULL;
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
        post_pyobject = (PyObject *)pyxine_new_post_pyobject(self, post, name, 1);

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
        PyDict_SetItemString_STEAL(dict, "origin", val);

        val = Py_BuildValue("s", mrls[i]->link);
        PyDict_SetItemString_STEAL(dict, "link", val);

        val = Py_BuildValue("s", mrls[i]->mrl);
        PyDict_SetItemString_STEAL(dict, "mrl", val);

        val = Py_BuildValue("i", mrls[i]->type);
        PyDict_SetItemString_STEAL(dict, "type", val);

        val = Py_BuildValue("i", mrls[i]->size);
        PyDict_SetItemString_STEAL(dict, "size", val);

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

PyObject *
_xine_config_entry_to_pydict(xine_cfg_entry_t *cfg)
{
    PyObject *dict = PyDict_New();
    PyDict_SetItemString_STEAL(dict, "key", PyString_FromString(cfg->key));
    switch(cfg->type) {
        case XINE_CONFIG_TYPE_UNKNOWN:
            PyDict_SetItemString(dict, "type", Py_None);
            break;

        case XINE_CONFIG_TYPE_RANGE:
            PyDict_SetItemString(dict, "type", (PyObject *)&PyInt_Type);
            PyDict_SetItemString_STEAL(dict, "min", PyInt_FromLong(cfg->range_min));
            PyDict_SetItemString_STEAL(dict, "max", PyInt_FromLong(cfg->range_max));
            PyDict_SetItemString_STEAL(dict, "value", PyInt_FromLong(cfg->num_value));
            PyDict_SetItemString_STEAL(dict, "default", PyInt_FromLong(cfg->num_default));
            break;

        case XINE_CONFIG_TYPE_STRING:
            PyDict_SetItemString(dict, "type", (PyObject *)&PyString_Type);
            PyDict_SetItemString_STEAL(dict, "value", PyString_FromString(cfg->str_value));
            PyDict_SetItemString_STEAL(dict, "default", PyString_FromString(cfg->str_default));
            break;

        case XINE_CONFIG_TYPE_ENUM:
        {
            int i;
            PyObject *enums = PyList_New(0);
            PyDict_SetItemString(dict, "type", (PyObject *)&PyTuple_Type);

            for (i = 0; cfg->enum_values[i]; i++) {
                PyObject *val = PyString_FromString(cfg->enum_values[i]);
                PyList_Append_STEAL(enums, val);
                if (i == cfg->num_value)
                    PyDict_SetItemString(dict, "value", val);
                if (i == cfg->num_default)
                    PyDict_SetItemString(dict, "default", val);
            }
            PyDict_SetItemString_STEAL(dict, "enums", enums);
            break;
        }
        case XINE_CONFIG_TYPE_NUM:
            PyDict_SetItemString(dict, "type", (PyObject *)&PyInt_Type);
            PyDict_SetItemString_STEAL(dict, "value", PyInt_FromLong(cfg->num_value));
            PyDict_SetItemString_STEAL(dict, "default", PyInt_FromLong(cfg->num_default));
            break;
        case XINE_CONFIG_TYPE_BOOL:
            PyDict_SetItemString(dict, "type", (PyObject *)&PyBool_Type);
            PyDict_SetItemString_STEAL(dict, "value", PyBool_FromLong(cfg->num_value));
            PyDict_SetItemString_STEAL(dict, "default", PyBool_FromLong(cfg->num_default));
            break;
    }
    return dict;
}

PyObject *
Xine_PyObject_config_get_first_entry(Xine_PyObject *self, PyObject *args, PyObject *kwargs)
{
    xine_cfg_entry_t cfg;

    if (!xine_config_get_first_entry(self->xine, &cfg)) {
        PyErr_Format(xine_error, "Failed to get first config entry");
        return NULL;
    }

    return _xine_config_entry_to_pydict(&cfg);
}

PyObject *
Xine_PyObject_config_get_next_entry(Xine_PyObject *self, PyObject *args, PyObject *kwargs)
{
    xine_cfg_entry_t cfg;

    if (!xine_config_get_next_entry(self->xine, &cfg)) {
        Py_INCREF(Py_None);
        return Py_None;
    }

    return _xine_config_entry_to_pydict(&cfg);
}

PyObject *
Xine_PyObject_config_lookup_entry(Xine_PyObject *self, PyObject *args, PyObject *kwargs)
{
    xine_cfg_entry_t cfg;
    char *key;

    if (!PyArg_ParseTuple(args, "s", &key))
        return NULL;

    if (!xine_config_lookup_entry(self->xine, key, &cfg)) {
        Py_INCREF(Py_None);
        return Py_None;
    }
    return _xine_config_entry_to_pydict(&cfg);
}

PyObject *
Xine_PyObject_config_update_entry(Xine_PyObject *self, PyObject *args, PyObject *kwargs)
{
    xine_cfg_entry_t cfg;
    char *key;
    PyObject *value;

    if (!PyArg_ParseTuple(args, "sO", &key, &value))
        return NULL;

    if (!xine_config_lookup_entry(self->xine, key, &cfg)) {
        PyErr_Format(xine_error, "Unable to locate config entry '%s'", key);
        return NULL;
    }

    switch(cfg.type) {
        case XINE_CONFIG_TYPE_STRING:
            cfg.str_value = PyString_AsString(value);
            break;
        case XINE_CONFIG_TYPE_ENUM:
        case XINE_CONFIG_TYPE_RANGE:
        case XINE_CONFIG_TYPE_NUM:
        case XINE_CONFIG_TYPE_BOOL:
            cfg.num_value = PyLong_AsLong(value);
            break;
    }

    xine_config_update_entry(self->xine, &cfg);
    if (cfg.callback)
        cfg.callback(cfg.callback_data, &cfg);

    Py_INCREF(Py_None);
    return Py_None;
}

PyMethodDef Xine_PyObject_methods[] = {
    {"list_plugins", (PyCFunction) Xine_PyObject_list_plugins, METH_VARARGS },
    {"load_video_output_plugin", (PyCFunction) Xine_PyObject_load_video_output_plugin, METH_VARARGS | METH_KEYWORDS},
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

    {"config_get_first_entry", (PyCFunction) Xine_PyObject_config_get_first_entry, METH_VARARGS },
    {"config_get_next_entry", (PyCFunction) Xine_PyObject_config_get_next_entry, METH_VARARGS },
    {"config_lookup_entry", (PyCFunction) Xine_PyObject_config_lookup_entry, METH_VARARGS },
    {"config_update_entry", (PyCFunction) Xine_PyObject_config_update_entry, METH_VARARGS },
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

PyObject *
Xine_get_object_by_id(PyObject *module, PyObject *args, PyObject *kwargs)
{
    PyObject *o;
    int ptr;

    if (!PyArg_ParseTuple(args, "i", &ptr))
        return NULL;

    o = xine_object_to_pyobject_find((void *)ptr);
    if (!o)
        o = Py_None;
    Py_INCREF(o);
    return o;
}

PyMethodDef xine_methods[] = {
    {"get_version", (PyCFunction) Xine_get_version, METH_VARARGS },
    {"get_object_by_id", (PyCFunction) Xine_get_object_by_id, METH_VARARGS },
    {NULL}
};


void **get_module_api(char *module)
{
    PyObject *m, *c_api;
    void **ptrs;

    m = PyImport_ImportModule(module);
    if (m == NULL)
       return NULL;
    c_api = PyObject_GetAttrString(m, "_C_API");
    if (c_api == NULL || !PyCObject_Check(c_api))
        return NULL;
    ptrs = (void **)PyCObject_AsVoidPtr(c_api);
    Py_DECREF(c_api);
    return ptrs;
}


#define INIT_XINE_TYPE(s, label) \
    if (PyType_Ready(& s ## _PyObject_Type) < 0) return; \
    Py_INCREF(& s ## _PyObject_Type); \
    PyModule_AddObject(m, label, (PyObject *)& s ## _PyObject_Type)


void
init_xine()
{
    PyObject *m;
#ifdef HAVE_X11
    void **display_api_ptrs;
#endif

    m = Py_InitModule("_xine", xine_methods);
    xine_error = PyErr_NewException("xine.XineError", NULL, NULL);
    Py_INCREF(xine_error);
    PyModule_AddObject(m, "XineError", xine_error);

    INIT_XINE_TYPE(Xine, "Xine");
    INIT_XINE_TYPE(Xine_VO_Driver, "VODriver");
    INIT_XINE_TYPE(Xine_Video_Port, "VideoPort");
    INIT_XINE_TYPE(Xine_Audio_Port, "AudioPort");
    INIT_XINE_TYPE(Xine_Stream, "Stream");
    INIT_XINE_TYPE(Xine_Post, "Post");
    INIT_XINE_TYPE(Xine_Post_In, "PostIn");
    INIT_XINE_TYPE(Xine_Post_Out, "PostOut");
    INIT_XINE_TYPE(Xine_Event_Queue, "EventQueue");
    INIT_XINE_TYPE(Xine_Event, "Event");

    if (xine_object_to_pyobject_dict == NULL)
        xine_object_to_pyobject_dict = PyDict_New();

#ifdef HAVE_X11
    // We need kaa.display for X11 support.
    display_api_ptrs = get_module_api("kaa.display._X11");
    if (display_api_ptrs) {
        // Declared in drivers/x11.c, which is only compiled/linked if HAVE_X11
        X11Window_PyObject_Type = display_api_ptrs[1];
        x11window_object_decompose = display_api_ptrs[2];
    } else {
        /* kaa.display not compiled with X11 support but kaa.xine wants to be.
         * We should probably output a warning or something here.
         */
        X11Window_PyObject_Type = NULL;
    }
#endif

    PyEval_InitThreads();
}
