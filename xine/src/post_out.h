#ifndef __POST_OUT_H_
#define __POST_OUT_H_
#include "config.h"

#include <Python.h>
#include <xine.h>
#include "post.h"

#define Xine_Post_Out_PyObject_Check(v) ((v)->ob_type == &Xine_Post_Out_PyObject_Type)

typedef struct {
    PyObject_HEAD

    xine_post_out_t *post_out;
    int xine_object_owner;
    xine_t *xine;

    PyObject *owner_pyobject,
             *port, // Video or Audio port for this PostOut
             *wire_object, // if this PostOut is for a stream, the wire target
             *wrapper;
} Xine_Post_Out_PyObject;

extern PyTypeObject Xine_Post_Out_PyObject_Type;

PyObject *Xine_Post_Out_PyObject__new(PyTypeObject *, PyObject *, PyObject *);
Xine_Post_Out_PyObject *pyxine_new_post_out_pyobject(PyObject *, xine_post_out_t *, int);


#endif
