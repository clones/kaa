#include <Python.h>
#include <Evas.h>

#include "object.h"
#include "textblock.h"


PyObject *
Evas_Object_PyObject_textblock_clear(Evas_Object_PyObject * self, PyObject * args)
{
    evas_object_textblock_clear(self->object);
    return Py_INCREF(Py_None), Py_None;
}

PyObject *
Evas_Object_PyObject_textblock_style_set(Evas_Object_PyObject * self, PyObject * args)
{
    char *style;
    Evas_Textblock_Style *st;

    if (!PyArg_ParseTuple(args, "s", &style))
        return NULL;

    st = evas_textblock_style_new();
    evas_textblock_style_set(st, style);
    evas_object_textblock_style_set(self->object, st);
    evas_textblock_style_free(st);
    return Py_INCREF(Py_None), Py_None;

}
PyObject *
Evas_Object_PyObject_textblock_markup_set(Evas_Object_PyObject * self, PyObject * args)
{
    char *markup;

    if (!PyArg_ParseTuple(args, "s", &markup))
        return NULL;

    evas_object_textblock_text_markup_set(self->object, markup);
    return Py_INCREF(Py_None), Py_None;

}

PyObject *
Evas_Object_PyObject_textblock_markup_get(Evas_Object_PyObject * self, PyObject * args)
{
    const char *markup = evas_object_textblock_text_markup_get(self->object);
    if (!markup)
        return Py_INCREF(Py_None), Py_None;
    return PyString_FromString(markup);
}

PyObject *
Evas_Object_PyObject_textblock_size_formatted_get(Evas_Object_PyObject * self, PyObject * args)
{
    int w, h;
    evas_object_textblock_size_formatted_get(self->object, &w, &h);
    return Py_BuildValue("(ii)", w, h);
}

PyObject *
Evas_Object_PyObject_textblock_size_native_get(Evas_Object_PyObject * self, PyObject * args)
{
    int w, h;
    evas_object_textblock_size_native_get(self->object, &w, &h);
    return Py_BuildValue("(ii)", w, h);
}

