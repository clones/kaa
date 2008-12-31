#include "xine.h"
#include "post.h"
#include "post_in.h"
#include "post_out.h"
#include "stream.h"
#include "vo_driver.h"
#include "video_port.h"
#include "structmember.h"

// Owner must be a Xine or VideoPort object
Xine_VO_Driver_PyObject *
pyxine_new_vo_driver_pyobject(Xine_PyObject *xine, void *owner, vo_driver_t *driver, int do_dispose)
{
    Xine_VO_Driver_PyObject *o;
    PyObject *owner_pyobject;

    o = (Xine_VO_Driver_PyObject *)xine_object_to_pyobject_find(driver);
    if (o) {
        Py_INCREF(o);
        return o;
    }

    // Verify owner
    owner_pyobject = xine_object_to_pyobject_find(owner);
    if (!owner_pyobject ||
        (!Xine_Video_Port_PyObject_Check(owner_pyobject) &&
         !Xine_PyObject_Check(owner_pyobject))) {
            PyErr_Format(xine_error, "Unsupported owner for VO Driver Port object");
            return NULL;
    }

    o = (Xine_VO_Driver_PyObject *)Xine_VO_Driver_PyObject__new(&Xine_VO_Driver_PyObject_Type, NULL, NULL);
    if (!o)
        return NULL;

    o->driver = driver;
    o->do_dispose = do_dispose;
    o->xine = xine;
    Py_INCREF(o->xine);

    xine_object_to_pyobject_register(driver, (PyObject *)o);
    return o;
}


PyObject *
Xine_VO_Driver_PyObject__new(PyTypeObject * type, PyObject * args,
                              PyObject * kwargs)
{
    Xine_VO_Driver_PyObject *self;

    if (args) {
        PyErr_SetString(xine_error, "Don't call me directly");
        return NULL;
    }

    self = (Xine_VO_Driver_PyObject *) type->tp_alloc(type, 0);
    self->driver = NULL;
    self->xine = NULL;
    self->wrapper = Py_None;
    Py_INCREF(Py_None);
    return (PyObject *) self;
}

static int
Xine_VO_Driver_PyObject__init(Xine_VO_Driver_PyObject * self,
                               PyObject * args, PyObject * kwds)
{
    return 0;
}

static PyMemberDef Xine_VO_Driver_PyObject_members[] = {
    {"wrapper", T_OBJECT_EX, offsetof(Xine_VO_Driver_PyObject, wrapper), 0, "Wrapper object"},
    {NULL}
};


void
Xine_VO_Driver_PyObject__dealloc(Xine_VO_Driver_PyObject * self)
{
    printf("DEalloc VO Driver: %p (owner=%d)\n", self->driver, self->do_dispose);
    if (self->driver && self->do_dispose) {
        Py_BEGIN_ALLOW_THREADS
        self->driver->dispose(self->driver);
        Py_END_ALLOW_THREADS
    }
    Py_DECREF(self->wrapper);
    Py_DECREF(self->xine);
    //Xine_VO_Driver_PyObject__clear(self);

    xine_object_to_pyobject_unregister(self->driver);

    if (self->driver_info && self->driver_info->dealloc_cb)
        self->driver_info->dealloc_cb(self->driver_info);

    self->ob_type->tp_free((PyObject *) self);
}

PyObject *
Xine_VO_Driver_PyObject_get_owner(Xine_VO_Driver_PyObject *self, PyObject *args, PyObject *kwargs)
{
    PyObject *owner = xine_object_to_pyobject_find(self->owner);
    if (!owner)
        owner = Py_None;
    Py_INCREF(owner);
    return owner;
}


PyObject *
Xine_VO_Driver_PyObject_get_port(Xine_VO_Driver_PyObject *self, PyObject *args, PyObject *kwargs)
{
    xine_video_port_t *vo_port;
    Xine_Video_Port_PyObject *vo;
    PyObject *owner_pyobject = xine_object_to_pyobject_find(self->owner);

    if (owner_pyobject && Xine_Video_Port_PyObject_Check(owner_pyobject)) {
        Py_INCREF(owner_pyobject);
        return owner_pyobject;
    }

    vo_port = _x_vo_new_port(self->xine->xine, self->driver, 0);
    vo = pyxine_new_video_port_pyobject(self->xine, self->xine->xine, vo_port, (PyObject *)self, 1);

    // VideoPort object assumes ownership of us.
    self->owner = vo_port;
    self->do_dispose = 0;

    return (PyObject *)vo;
}



PyMethodDef Xine_VO_Driver_PyObject_methods[] = {
    {"get_owner", (PyCFunction) Xine_VO_Driver_PyObject_get_owner, METH_VARARGS },
    {"get_port", (PyCFunction) Xine_VO_Driver_PyObject_get_port, METH_VARARGS },
    {NULL, NULL}
};

PyTypeObject Xine_VO_Driver_PyObject_Type = {
    PyObject_HEAD_INIT(NULL) 
    0,                          /* ob_size */
    "_xine.VODriver",               /* tp_name */
    sizeof(Xine_VO_Driver_PyObject),      /* tp_basicsize */
    0,                          /* tp_itemsize */
    (destructor) Xine_VO_Driver_PyObject__dealloc,        /* tp_dealloc */
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
    Py_TPFLAGS_DEFAULT | Py_TPFLAGS_BASETYPE, /* tp_flags */
    "Xine VO Driver Object",   /* tp_doc */
    0,                         /* tp_traverse */
    0,                         /* tp_clear */
    0,                         /* tp_richcompare */
    0,                         /* tp_weaklistoffset */
    0,                         /* tp_iter */
    0,                         /* tp_iternext */
    Xine_VO_Driver_PyObject_methods,     /* tp_methods */
    Xine_VO_Driver_PyObject_members,     /* tp_members */
    0,                         /* tp_getset */
    0,                         /* tp_base */
    0,                         /* tp_dict */
    0,                         /* tp_descr_get */
    0,                         /* tp_descr_set */
    0,                         /* tp_dictoffset */
    (initproc)Xine_VO_Driver_PyObject__init, /* tp_init */
    0,                         /* tp_alloc */
    Xine_VO_Driver_PyObject__new,        /* tp_new */
};


