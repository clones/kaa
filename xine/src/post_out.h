#ifndef __POST_OUT_H_
#define __POST_OUT_H_
#include "config.h"

#include <Python.h>
#include <xine.h>
#include "post.h"

#define Xine_Post_Out_PyObject_Check(v) ((v)->ob_type == &Xine_Post_Out_PyObject_Type)

typedef struct {
    PyObject_HEAD

    Xine_PyObject *xine;
    xine_post_out_t *post_out;
    void *owner;
    int do_dispose;

    PyObject *wrapper,
             *port; // Video/Audio Port this PostOut is wired to.
} Xine_Post_Out_PyObject;

extern PyTypeObject Xine_Post_Out_PyObject_Type;

PyObject *Xine_Post_Out_PyObject__new(PyTypeObject *, PyObject *, PyObject *);
Xine_Post_Out_PyObject *pyxine_new_post_out_pyobject(Xine_PyObject *, void *, xine_post_out_t *, int);


#endif
