#ifndef __POST_IN_H_
#define __POST_IN_H_
#include "config.h"

#include <Python.h>
#include <xine.h>


#define Xine_Post_In_PyObject_Check(v) ((v)->ob_type == &Xine_Post_In_PyObject_Type)

typedef struct {
    PyObject_HEAD

    Xine_PyObject *xine;
    xine_post_in_t *post_in;
    void *owner; // Post object
    int do_dispose;
    PyObject *post;

    PyObject *port, // Video or Audio port for this PostIn
             *wrapper;
} Xine_Post_In_PyObject;

extern PyTypeObject Xine_Post_In_PyObject_Type;

PyObject *Xine_Post_In_PyObject__new(PyTypeObject *, PyObject *, PyObject *);
Xine_Post_In_PyObject *pyxine_new_post_in_pyobject(Xine_PyObject *, void *, xine_post_in_t *, int);


#endif
