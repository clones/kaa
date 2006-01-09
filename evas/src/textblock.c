#include "object.h"
#include "textblock.h"
#include "structmember.h"


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

PyObject *
Evas_Object_PyObject_textblock_style_insets_get(Evas_Object_PyObject * self, PyObject * args)
{
    int l, r, t, b;
    evas_object_textblock_style_insets_get(self->object, &l, &r, &t, &b);
    return Py_BuildValue("(iiii)", l, r, t, b);
}

PyObject *
Evas_Object_PyObject_textblock_cursor_get(Evas_Object_PyObject *self, PyObject * args)
{
    const Evas_Textblock_Cursor *cursor = evas_object_textblock_cursor_get(self->object);
    if (!cursor) {
        Py_INCREF(Py_None);
        return Py_None;
    }
    return (PyObject *)wrap_evas_textblock_cursor((Evas_Textblock_Cursor *)cursor, self);
}

PyObject *
Evas_Object_PyObject_textblock_line_number_geometry_get(Evas_Object_PyObject *self, PyObject * args)
{
    int x, y, w, h, line;
    if (!PyArg_ParseTuple(args, "i", &line))
        return NULL;
    if (!evas_object_textblock_line_number_geometry_get(self->object, line, &x, &y, &w, &h)) {
        Py_INCREF(Py_None);
        return Py_None;
    }
    return Py_BuildValue("(iiii)", x, y, w, h);
}



/****************************************************************************
 * Cursor Type
 *********************/


PyObject *
Evas_Textblock_Cursor_PyObject__new(PyTypeObject *type, PyObject * args, PyObject * kwargs)
{
    Evas_Textblock_Cursor_PyObject *self;
    Evas_Object_PyObject *textblock = NULL;
    if (args != NULL && !PyArg_ParseTuple(args, "O!", &Evas_Object_PyObject_Type, &textblock))
        return NULL;

    self = (Evas_Textblock_Cursor_PyObject *)type->tp_alloc(type, 0);
    if (textblock) {
        self->cursor = evas_object_textblock_cursor_new(textblock->object);
        self->textblock = textblock;
        Py_INCREF(textblock);
    }
    printf("Textblock Cursor alloc: %p\n", self->cursor);
    return (PyObject *)self;
}

static int
Evas_Textblock_Cursor_PyObject__init(Evas_Textblock_Cursor_PyObject *self, PyObject *args, PyObject *kwds)
{
    return 0;
}

void
Evas_Textblock_Cursor_PyObject__dealloc(Evas_Textblock_Cursor_PyObject * self)
{
    printf("Textblock Cursor dealloc: %p\n", self->cursor);
    if (self->cursor)
        evas_textblock_cursor_free(self->cursor);
    if (self->textblock) {
        Py_DECREF(self->textblock);
    }
    self->ob_type->tp_free((PyObject*)self);
}

Evas_Textblock_Cursor_PyObject *
wrap_evas_textblock_cursor(Evas_Textblock_Cursor *cursor, Evas_Object_PyObject *textblock)
{
    Evas_Textblock_Cursor_PyObject *o;

    o = (Evas_Textblock_Cursor_PyObject *)Evas_Textblock_Cursor_PyObject__new(&Evas_Textblock_Cursor_PyObject_Type, NULL, NULL);
    if (!o)
        return NULL;
    o->cursor = cursor;
    o->textblock = textblock;
    Py_INCREF(textblock);
    return o;
}


PyObject *
Evas_Textblock_Cursor_PyObject__copy(Evas_Textblock_Cursor_PyObject *self, PyObject * args)
{
    Evas_Textblock_Cursor *new_cursor = evas_object_textblock_cursor_new(self->textblock->object);
    evas_textblock_cursor_copy(self->cursor, new_cursor);
    return (PyObject *)wrap_evas_textblock_cursor(new_cursor, self->textblock);
}

PyObject *
Evas_Textblock_Cursor_PyObject__char_coord_set(Evas_Textblock_Cursor_PyObject *self, PyObject * args)
{
    int x, y, ret;
    if (!PyArg_ParseTuple(args, "ii", &x, &y))
        return NULL;

    ret = evas_textblock_cursor_char_coord_set(self->cursor, x, y);
    return PyBool_FromLong(ret);
}

PyObject *
Evas_Textblock_Cursor_PyObject__char_geometry_get(Evas_Textblock_Cursor_PyObject *self, PyObject * args)
{
    int x, y, w, h, line;
    line  = evas_textblock_cursor_char_geometry_get(self->cursor, &x, &y, &w, &h);
    if (line == -1) {
        Py_INCREF(Py_None);
        return Py_None;
    }
    return Py_BuildValue("i(iiii)", line, x, y, w, h);
}


PyObject *
Evas_Textblock_Cursor_PyObject__char_delete(Evas_Textblock_Cursor_PyObject *self, PyObject * args)
{
    evas_textblock_cursor_char_delete(self->cursor);
    Py_INCREF(Py_None);
    return Py_None;
}

PyObject *
Evas_Textblock_Cursor_PyObject__range_delete(Evas_Textblock_Cursor_PyObject *self, PyObject * args)
{
    Evas_Textblock_Cursor_PyObject *cur2;
    if (!PyArg_ParseTuple(args, "O!", &Evas_Textblock_Cursor_PyObject_Type, &cur2))
        return NULL;

    evas_textblock_cursor_range_delete(self->cursor, cur2->cursor);
    Py_INCREF(Py_None);
    return Py_None;
}

PyObject *
Evas_Textblock_Cursor_PyObject__range_text_get(Evas_Textblock_Cursor_PyObject *self, PyObject * args)
{
    Evas_Textblock_Cursor_PyObject *cur2;
    int format;
    char *str;
    if (!PyArg_ParseTuple(args, "O!i", &Evas_Textblock_Cursor_PyObject_Type, &cur2, &format))
        return NULL;

    str = evas_textblock_cursor_range_text_get(self->cursor, cur2->cursor, format);
    return Py_BuildValue("s", str); 
}

PyObject *
Evas_Textblock_Cursor_PyObject__pos_get(Evas_Textblock_Cursor_PyObject *self, PyObject * args)
{
    int pos = evas_textblock_cursor_pos_get(self->cursor);
    return Py_BuildValue("i", pos);
}

PyObject *
Evas_Textblock_Cursor_PyObject__pos_set(Evas_Textblock_Cursor_PyObject *self, PyObject * args)
{
    int pos;
    if (!PyArg_ParseTuple(args, "i", &pos))
        return NULL;

    evas_textblock_cursor_pos_set(self->cursor, pos);
    Py_INCREF(Py_None);
    return Py_None;
}

PyObject *
Evas_Textblock_Cursor_PyObject__char_first(Evas_Textblock_Cursor_PyObject *self, PyObject * args)
{
    evas_textblock_cursor_char_first(self->cursor);
    Py_INCREF(Py_None);
    return Py_None;
}

PyObject *
Evas_Textblock_Cursor_PyObject__char_prev(Evas_Textblock_Cursor_PyObject *self, PyObject * args)
{
    int ret = evas_textblock_cursor_char_prev(self->cursor);
    return PyBool_FromLong(ret);
}

PyObject *
Evas_Textblock_Cursor_PyObject__char_next(Evas_Textblock_Cursor_PyObject *self, PyObject * args)
{
    int ret = evas_textblock_cursor_char_next(self->cursor);
    return PyBool_FromLong(ret);
}
PyObject *
Evas_Textblock_Cursor_PyObject__char_last(Evas_Textblock_Cursor_PyObject *self, PyObject * args)
{
    evas_textblock_cursor_char_last(self->cursor);
    Py_INCREF(Py_None);
    return Py_None;
}

PyObject *
Evas_Textblock_Cursor_PyObject__line_first(Evas_Textblock_Cursor_PyObject *self, PyObject * args)
{
    evas_textblock_cursor_line_first(self->cursor);
    Py_INCREF(Py_None);
    return Py_None;
}

PyObject *
Evas_Textblock_Cursor_PyObject__line_last(Evas_Textblock_Cursor_PyObject *self, PyObject * args)
{
    evas_textblock_cursor_line_last(self->cursor);
    Py_INCREF(Py_None);
    return Py_None;
}

PyObject *
Evas_Textblock_Cursor_PyObject__line_set(Evas_Textblock_Cursor_PyObject *self, PyObject * args)
{
    int line, ret;
    if (!PyArg_ParseTuple(args, "i", &line))
        return NULL;

    ret = evas_textblock_cursor_line_set(self->cursor, line);
    return PyBool_FromLong(ret);
}

PyObject *
Evas_Textblock_Cursor_PyObject__line_coord_set(Evas_Textblock_Cursor_PyObject *self, PyObject * args)
{
    int y, line;
    if (!PyArg_ParseTuple(args, "i", &y))
        return NULL;

    line = evas_textblock_cursor_line_coord_set(self->cursor, y);
    return Py_BuildValue("i", line);
}

PyObject *
Evas_Textblock_Cursor_PyObject__line_geometry_get(Evas_Textblock_Cursor_PyObject *self, PyObject * args)
{
    int x, y, w, h;
    evas_textblock_cursor_line_geometry_get(self->cursor, &x, &y, &w, &h);
    return Py_BuildValue("(iiii)", x, y, w, h);
}

PyObject *
Evas_Textblock_Cursor_PyObject__node_text_get(Evas_Textblock_Cursor_PyObject *self, PyObject * args)
{
    const char *str = evas_textblock_cursor_node_text_get(self->cursor);
    return Py_BuildValue("s", str);
}

PyObject *
Evas_Textblock_Cursor_PyObject__node_first(Evas_Textblock_Cursor_PyObject *self, PyObject * args)
{
    evas_textblock_cursor_node_first(self->cursor);
    Py_INCREF(Py_None);
    return Py_None;
}

PyObject *
Evas_Textblock_Cursor_PyObject__node_prev(Evas_Textblock_Cursor_PyObject *self, PyObject * args)
{
    int ret = evas_textblock_cursor_node_prev(self->cursor);
    return PyBool_FromLong(ret);
}

PyObject *
Evas_Textblock_Cursor_PyObject__node_next(Evas_Textblock_Cursor_PyObject *self, PyObject * args)
{
    int ret = evas_textblock_cursor_node_next(self->cursor);
    return PyBool_FromLong(ret);
}

PyObject *
Evas_Textblock_Cursor_PyObject__node_last(Evas_Textblock_Cursor_PyObject *self, PyObject * args)
{
    evas_textblock_cursor_node_last(self->cursor);
    Py_INCREF(Py_None);
    return Py_None;
}

PyObject *
Evas_Textblock_Cursor_PyObject__node_delete(Evas_Textblock_Cursor_PyObject *self, PyObject * args)
{
    evas_textblock_cursor_node_delete(self->cursor);
    Py_INCREF(Py_None);
    return Py_None;
}

PyObject *
Evas_Textblock_Cursor_PyObject__node_format_get(Evas_Textblock_Cursor_PyObject *self, PyObject * args)
{
    const char *str = evas_textblock_cursor_node_format_get(self->cursor);
    return Py_BuildValue("s", str);
}


PyObject *
Evas_Textblock_Cursor_PyObject__text_append(Evas_Textblock_Cursor_PyObject *self, PyObject * args)
{
    char *text;
    if (!PyArg_ParseTuple(args, "s", &text))
        return NULL;

    evas_textblock_cursor_text_append(self->cursor, text);
    Py_INCREF(Py_None);
    return Py_None;
}



PyMethodDef Evas_Textblock_Cursor_PyObject_methods[] = {
    {"copy", (PyCFunction) Evas_Textblock_Cursor_PyObject__copy, METH_VARARGS},
    {"char_coord_set", (PyCFunction) Evas_Textblock_Cursor_PyObject__char_coord_set, METH_VARARGS},
    {"char_geometry_get", (PyCFunction) Evas_Textblock_Cursor_PyObject__char_geometry_get, METH_VARARGS},
    {"pos_get", (PyCFunction) Evas_Textblock_Cursor_PyObject__pos_get, METH_VARARGS},
    {"pos_set", (PyCFunction) Evas_Textblock_Cursor_PyObject__pos_set, METH_VARARGS},
    {"char_delete", (PyCFunction) Evas_Textblock_Cursor_PyObject__char_delete, METH_VARARGS},
    {"range_delete", (PyCFunction) Evas_Textblock_Cursor_PyObject__range_delete, METH_VARARGS},
    {"range_text_get", (PyCFunction) Evas_Textblock_Cursor_PyObject__range_text_get, METH_VARARGS},
    {"char_first", (PyCFunction) Evas_Textblock_Cursor_PyObject__char_first, METH_VARARGS},
    {"char_prev", (PyCFunction) Evas_Textblock_Cursor_PyObject__char_prev, METH_VARARGS},
    {"char_next", (PyCFunction) Evas_Textblock_Cursor_PyObject__char_next, METH_VARARGS},
    {"char_last", (PyCFunction) Evas_Textblock_Cursor_PyObject__char_last, METH_VARARGS},
    {"line_first", (PyCFunction) Evas_Textblock_Cursor_PyObject__line_first, METH_VARARGS},
    {"line_last", (PyCFunction) Evas_Textblock_Cursor_PyObject__line_last, METH_VARARGS},
    {"line_set", (PyCFunction) Evas_Textblock_Cursor_PyObject__line_set, METH_VARARGS},
    {"line_coord_set", (PyCFunction) Evas_Textblock_Cursor_PyObject__line_coord_set, METH_VARARGS},
    {"line_geometry_get", (PyCFunction) Evas_Textblock_Cursor_PyObject__line_geometry_get, METH_VARARGS},
    {"node_text_get", (PyCFunction) Evas_Textblock_Cursor_PyObject__node_text_get, METH_VARARGS},
    {"node_first", (PyCFunction) Evas_Textblock_Cursor_PyObject__node_first, METH_VARARGS},
    {"node_prev", (PyCFunction) Evas_Textblock_Cursor_PyObject__node_prev, METH_VARARGS},
    {"node_next", (PyCFunction) Evas_Textblock_Cursor_PyObject__node_next, METH_VARARGS},
    {"node_last", (PyCFunction) Evas_Textblock_Cursor_PyObject__node_last, METH_VARARGS},
    {"node_delete", (PyCFunction) Evas_Textblock_Cursor_PyObject__node_delete, METH_VARARGS},
    {"node_format_get", (PyCFunction) Evas_Textblock_Cursor_PyObject__node_format_get, METH_VARARGS},
    {"text_append", (PyCFunction) Evas_Textblock_Cursor_PyObject__text_append, METH_VARARGS},
    {NULL, NULL}
};

int
Evas_Textblock_Cursor_PyObject__compare(Evas_Textblock_Cursor_PyObject *a, Evas_Textblock_Cursor_PyObject *b)
{
    return evas_textblock_cursor_compare(a->cursor, b->cursor);
}


PyTypeObject Evas_Textblock_Cursor_PyObject_Type = {
    PyObject_HEAD_INIT(NULL)
    0,                          /* ob_size */
    "_evas.TextBlockCursor",             /* tp_name */
    sizeof(Evas_Textblock_Cursor_PyObject),       /* tp_basicsize */
    0,                          /* tp_itemsize */
    (destructor) Evas_Textblock_Cursor_PyObject__dealloc,  /* tp_dealloc */
    0,                          /* tp_print */
    0,                          /* tp_getattr */
    0,                          /* tp_setattr */
    (cmpfunc) Evas_Textblock_Cursor_PyObject__compare,   /* tp_compare */
    0,                          /* tp_repr */
    0,                          /* tp_as_number */
    0,                          /* tp_as_sequence */
    0,                          /* tp_as_mapping */
    0,                          /* tp_hash */
    0,                          /* tp_call */
    0,                          /* tp_str */
    PyObject_GenericGetAttr,        /* tp_getattro */
    PyObject_GenericSetAttr,        /* tp_setattro */
    0,                          /* tp_as_buffer */
    Py_TPFLAGS_DEFAULT | Py_TPFLAGS_BASETYPE,         /* tp_flags */
    "Evas Textblock Cursor",               /* tp_doc */
    0,   /* tp_traverse */
    0,           /* tp_clear */
    0,                     /* tp_richcompare */
    0,                     /* tp_weaklistoffset */
    0,                     /* tp_iter */
    0,                     /* tp_iternext */
    Evas_Textblock_Cursor_PyObject_methods,  /* tp_methods */
    0,                         /* tp_members */
    0,                         /* tp_getset */
    0,                         /* tp_base */
    0,                         /* tp_dict */
    0,                         /* tp_descr_get */
    0,                         /* tp_descr_set */
    0,                         /* tp_dictoffset */
    (initproc)Evas_Textblock_Cursor_PyObject__init,  /* tp_init */
    0,                         /* tp_alloc */
    Evas_Textblock_Cursor_PyObject__new, /* tp_new */
};

