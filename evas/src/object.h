#include "evas.h"

#define Evas_Object_PyObject_Check(v) ((v)->ob_type == &Evas_Object_PyObject_Type)

typedef struct {
    PyObject_HEAD
    Evas_Object *object;

} Evas_Object_PyObject;

extern PyTypeObject Evas_Object_PyObject_Type;

Evas_Object_PyObject *wrap_evas_object(Evas_Object *, Evas_PyObject *);

