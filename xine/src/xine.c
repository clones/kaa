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

///


static int
Xine_PyObject__clear(Xine_PyObject *self)
{
    PyObject *tmp;
    if (self->dependencies) {
        tmp = self->dependencies;
        self->dependencies= 0;
        Py_DECREF(tmp);
    }
    return 0;
}

static int
Xine_PyObject__traverse(Xine_PyObject *self, visitproc visit, void *arg)
{
    if (self->dependencies) {
        int ret = visit(self->dependencies, arg);
        if (ret != 0)
            return ret;
    }
    return 0;
}

PyObject *
Xine_PyObject__new(PyTypeObject *type, PyObject * args, PyObject * kwargs)
{
    Xine_PyObject *self;

    self = (Xine_PyObject *)type->tp_alloc(type, 0);
    self->dependencies = PyList_New(0);
    self->wrapper = Py_None;
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
    return 0;
}

static PyMemberDef Xine_PyObject_members[] = {
    {"dependencies", T_OBJECT_EX, offsetof(Xine_PyObject, dependencies), 0, "Dependencies"},
    {"wrapper", T_OBJECT_EX, offsetof(Xine_PyObject, wrapper), 0, "Wrapper object"},
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
    int i;

    if (!PyArg_ParseTuple(args, "s", &type))
        return NULL;
    if (!strcmp(type, "video"))
        list = xine_list_video_output_plugins(self->xine);
    else if (!strcmp(type, "audio"))
        list = xine_list_audio_output_plugins(self->xine);
    else if (!strcmp(type, "post"))
        list = xine_list_post_plugins(self->xine);
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

// XXX Temporary.  Obviously. :)
static void frame_output_cb(void *data, int video_width, int video_height,
                double video_pixel_aspect, int *dest_x, int *dest_y,
                int *dest_width, int *dest_height,
                double *dest_pixel_aspect, int *win_x, int *win_y) {
  *dest_x            = 0;
  *dest_y            = 0;
  *win_x             = 0;
  *win_y             = 0;
  *dest_width        = 640;//width;
  *dest_height       = 480;//height;
  *dest_pixel_aspect = 1;
  //printf("frame_output_cb: Video width: %d, heigh: %d, pixel aspect: %f %x\n", video_width, video_height, video_pixel_aspect, data);
}


PyObject *
Xine_PyObject_open_video_driver(Xine_PyObject *self, PyObject *args, PyObject *kwargs)
{
    char *driver;
    xine_video_port_t *vo_port = NULL;

    if (!PyArg_ParseTuple(args, "s", &driver))
        return NULL;

    if (!strcmp(driver, "xv") || !strcmp(driver, "auto")) {
        PyObject *window;
        x11_visual_t vis;

        window = PyDict_GetItemString(kwargs, "window");
        if (!x11window_object_decompose(window, &vis.d, (Display **)&vis.display))
            return NULL;
        vis.screen = DefaultScreen(vis.display);
        vis.user_data = NULL;
        vis.frame_output_cb = frame_output_cb;
        vis.user_data = window;
        vo_port = xine_open_video_driver(self->xine, driver, XINE_VISUAL_TYPE_X11, (void *)&vis);
    } else if (!strcmp(driver, "none")) {
        vo_port = xine_open_video_driver(self->xine, driver, XINE_VISUAL_TYPE_NONE, 0);
    }
        
    if (!vo_port) {
        PyErr_Format(xine_error, "Failed to open driver: %s", driver);
        return NULL;
    }
    return (PyObject *)pyxine_new_video_port_pyobject(self, vo_port, 1);
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

    return (PyObject *)pyxine_new_audio_port_pyobject(self, ao_port, 1);
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
    return (PyObject *)pyxine_new_stream_pyobject(self, stream, ao, vo, 1);
}

PyObject *
Xine_PyObject_post_init(Xine_PyObject *self, PyObject *args, PyObject *kwargs)
{
    char *name;
    int inputs, i;
    PyObject *audio_targets, *video_targets;
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

    free(ao);
    free(vo);
    
    if (!post) {
        PyErr_Format(xine_error, "Failed to initialize post plugin.");
        return NULL;
    }

    {
        /*
        xine_post_in_t *input_api = (xine_post_in_t *) xine_post_input(post, "parameters");
        xine_post_api_t *api = (xine_post_api_t *)input_api->data;
        int data = 142;
        api->set_parameters(post, &data);
        printf("POST API: %x\n", input_api);
        */
    }

    return (PyObject *)pyxine_new_post_pyobject(self, post, audio_targets, video_targets, 1);

}

PyMethodDef Xine_PyObject_methods[] = {
    {"list_plugins", (PyCFunction) Xine_PyObject_list_plugins, METH_VARARGS | METH_KEYWORDS},
    {"open_video_driver", (PyCFunction) Xine_PyObject_open_video_driver, METH_VARARGS | METH_KEYWORDS},
    {"open_audio_driver", (PyCFunction) Xine_PyObject_open_audio_driver, METH_VARARGS | METH_KEYWORDS},
    {"stream_new", (PyCFunction) Xine_PyObject_stream_new, METH_VARARGS | METH_KEYWORDS},
    {"post_init", (PyCFunction) Xine_PyObject_post_init, METH_VARARGS | METH_KEYWORDS},
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


PyMethodDef xine_methods[] = {
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

}
