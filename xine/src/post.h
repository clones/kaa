#ifndef __POST_H_
#define __POST_H_
#include "config.h"

#include <Python.h>
#include <xine.h>
#include <xine/post.h>


#define Xine_Post_PyObject_Check(v) ((v)->ob_type == &Xine_Post_PyObject_Type)

typedef struct {
    PyObject_HEAD

    xine_post_t *post;
    int xine_object_owner;

    PyObject *owner_pyobject;
    xine_t *xine;
    PyObject *outputs, *inputs;
    PyObject *name; // post plugin identifier

    PyObject *wrapper;
} Xine_Post_PyObject;

extern PyTypeObject Xine_Post_PyObject_Type;

PyObject *Xine_Post_PyObject__new(PyTypeObject *, PyObject *, PyObject *);
Xine_Post_PyObject *pyxine_new_post_pyobject(PyObject *, xine_post_t *, char *, int);


#endif
