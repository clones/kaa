/*
 * ----------------------------------------------------------------------------
 * object.c - basic evas object wrapper
 * ----------------------------------------------------------------------------
 * $Id$
 *
 * ----------------------------------------------------------------------------
 * kaa.evas - An evas wrapper for Python
 * Copyright (C) 2006 Jason Tackaberry <tack@sault.org>
 *
 * First Edition: Jason Tackaberry <tack@sault.org>
 * Maintainer:    Jason Tackaberry <tack@sault.org>
 *
 * Please see the file AUTHORS for a complete list of authors.
 *
 * This library is free software; you can redistribute it and/or modify
 * it under the terms of the GNU Lesser General Public License version
 * 2.1 as published by the Free Software Foundation.
 *
 * This library is distributed in the hope that it will be useful, but
 * WITHOUT ANY WARRANTY; without even the implied warranty of
 * MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
 * Lesser General Public License for more details.
 *
 * You should have received a copy of the GNU Lesser General Public
 * License along with this library; if not, write to the Free Software
 * Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA
 * 02110-1301 USA
 *
 * ----------------------------------------------------------------------------
 */

#include <Python.h>
#include <Evas.h>

#include "object.h"
#include "image.h"
#include "text.h"
#include "textblock.h"
#include "gradient.h"

PyObject *
Evas_Object_PyObject__new(PyTypeObject *type, PyObject * args, PyObject * kwargs)
{
    Evas_Object_PyObject *self;
    self = (Evas_Object_PyObject *)type->tp_alloc(type, 0);
    return (PyObject *)self;
}

static int
Evas_Object_PyObject__init(Evas_Object_PyObject *self, PyObject *args, PyObject *kwds)
{
    self->object = 0;
    return 0;
}

typedef struct {
    int type; // 0 = clear, 1 = visit
    visitproc visit;
    void *arg;
    int ret;
} foreach_func_data;   

Evas_Bool
Evas_Object_PyObject_free_attr(Evas_Hash * attrs, const char *key, void *data,
                        void *fdata)
{
    foreach_func_data *d = (foreach_func_data *)fdata;
    if (!data)
        return 0;
    //printf("Attr foreach: %s (visit=%d)\n", key, d->type);
    if (d->type == 0) {
        Py_DECREF((PyObject *)data);
        return 1;
    } else {
        d->ret = d->visit(data, d->arg);
        return d->ret != 0;
    }
}

static int
Evas_Object_PyObject__clear(Evas_Object_PyObject *self)
{
    Evas_PyObject *evas;
    Evas_Hash *attrs;
    long ref;

    ref = (long)evas_object_data_get(self->object, "ref") - 1;
    evas_object_data_set(self->object, "ref", (void *)ref);

    //printf("Object refcount: %d\n", ref);
    if (ref) 
        return 0;

    evas = evas_object_data_get(self->object, "evas_pyobject");
    attrs = evas_object_data_get(self->object, "pyattrs");
    //fprintf(stderr, "Evas Object CLEAR: %x %x\n", attrs, evas);

    if (attrs) {
        foreach_func_data d = { 0, 0, 0, 0 };
        evas_object_data_del(self->object, "pyattrs");
        evas_hash_foreach(attrs, Evas_Object_PyObject_free_attr, &d);
        evas_object_del(self->object);
        evas_hash_free(attrs);
    }

    if (evas) {
        evas_object_data_del(self->object, "evas_pyobject");
        Py_DECREF(evas);
    }

    return 0;
}


static int
Evas_Object_PyObject__traverse(Evas_Object_PyObject *self, visitproc visit, void *arg)
{
    Evas_PyObject *evas;
    Evas_Hash *attrs;
    int ret;

    if (evas_object_data_get(self->object, "ref"))
        return 0;

    attrs = evas_object_data_get(self->object, "pyattrs");
    //fprintf(stderr, "Evas Object TRAVERSE: %x %x\n", attrs, evas);

    if (attrs) {
        foreach_func_data d = { 1, visit, arg, 0 };
        evas_hash_foreach(attrs, Evas_Object_PyObject_free_attr, &d);
        if (d.ret != 0)
            return d.ret;
    }

    evas = evas_object_data_get(self->object, "evas_pyobject");
    if (evas) {
        ret = visit((PyObject *)evas, arg);
        if (ret != 0)
            return ret;
    }
    return 0;
}



void
Evas_Object_PyObject__dealloc(Evas_Object_PyObject * self)
{
    //printf("Evas object dealloc: %s\n", evas_object_type_get(self->object));
    Evas_Object_PyObject__clear(self);
    evas_object_del(self->object);
    self->ob_type->tp_free((PyObject*)self);
}

Evas_Object_PyObject *
wrap_evas_object(Evas_Object * evas_object, Evas_PyObject * evas)
{
    Evas_Object_PyObject *o;
    long ref;

    o = (Evas_Object_PyObject *)Evas_Object_PyObject__new(&Evas_Object_PyObject_Type, NULL, NULL);
    if (evas && !evas_object_data_get(evas_object, "evas_pyobject")) {
        Py_INCREF(evas);
        evas_object_data_set(evas_object, "evas_pyobject", evas);
    }

    // It's possible for multiple Evas_Object_PyObjects to wrap one
    // Evas_Object, so we maintain a refcount.
    ref = (long)evas_object_data_get(evas_object, "ref");
    evas_object_data_set(evas_object, "ref", (void *)ref+1);
    o->object = evas_object;
    return o;
}

/**************************************************************************/

PyObject *
Evas_Object_PyObject_type_get(Evas_Object_PyObject * self, PyObject * args)
{
    return Py_BuildValue("s", evas_object_type_get(self->object));
}

PyObject *
Evas_Object_PyObject_move(Evas_Object_PyObject * self, PyObject * args)
{
    int x, y;

    if (!PyArg_ParseTuple(args, "(ii)", &x, &y))
        return NULL;

    BENCH_START
    evas_object_move(self->object, x, y);
    BENCH_END
    return Py_INCREF(Py_None), Py_None;
}

PyObject *
Evas_Object_PyObject_resize(Evas_Object_PyObject * self, PyObject * args)
{
    int w, h;

    if (!PyArg_ParseTuple(args, "(ii)", &w, &h))
        return NULL;

    BENCH_START
    evas_object_resize(self->object, w, h);
    BENCH_END
    return Py_INCREF(Py_None), Py_None;
}

PyObject *
Evas_Object_PyObject_show(Evas_Object_PyObject * self, PyObject * args)
{
    BENCH_START
    evas_object_show(self->object);
    BENCH_END
    return Py_INCREF(Py_None), Py_None;
}

PyObject *
Evas_Object_PyObject_hide(Evas_Object_PyObject * self, PyObject * args)
{
    BENCH_START
    evas_object_hide(self->object);
    BENCH_END
    return Py_INCREF(Py_None), Py_None;
}

PyObject *
Evas_Object_PyObject_geometry_get(Evas_Object_PyObject * self, PyObject * args)
{
    Evas_Coord x, y, w, h;

    BENCH_START
    evas_object_geometry_get(self->object, &x, &y, &w, &h);
    BENCH_END
    return Py_BuildValue("((ii)(ii))", x, y, w, h);
}

PyObject *
Evas_Object_PyObject_evas_get(Evas_Object_PyObject * self, PyObject * args)
{
    PyObject *evas;

    BENCH_START
    evas = evas_object_data_get(self->object, "evas_pyobject");
    BENCH_END
    if (evas) {
        Py_INCREF(evas);
        return evas;
    }
    Py_INCREF(Py_None);
    return Py_None;
}

PyObject *
Evas_Object_PyObject_layer_set(Evas_Object_PyObject * self, PyObject * args)
{
    int layer;

    if (!PyArg_ParseTuple(args, "i", &layer))
        return NULL;

    BENCH_START
    evas_object_layer_set(self->object, layer);
    BENCH_END
    return Py_INCREF(Py_None), Py_None;
}

PyObject *
Evas_Object_PyObject_layer_get(Evas_Object_PyObject * self, PyObject * args)
{
    int layer;

    BENCH_START
    layer = evas_object_layer_get(self->object);
    BENCH_END

    return Py_BuildValue("i", layer);
}

PyObject *
Evas_Object_PyObject_visible_get(Evas_Object_PyObject * self, PyObject * args)
{
    int visible;
    BENCH_START
    visible = evas_object_visible_get(self->object);
    BENCH_END
    if (visible)
        return Py_INCREF(Py_True), Py_True;
    return Py_INCREF(Py_False), Py_False;
}

PyObject *
Evas_Object_PyObject_color_set(Evas_Object_PyObject * self, PyObject * args)
{
    int r, g, b, a;

    if (!PyArg_ParseTuple(args, "iiii", &r, &g, &b, &a))
        return NULL;

    BENCH_START
    evas_object_color_set(self->object, r, g, b, a);
    BENCH_END
    return Py_INCREF(Py_None), Py_None;
}

PyObject *
Evas_Object_PyObject_color_get(Evas_Object_PyObject * self, PyObject * args)
{
    int r, g, b, a;

    BENCH_START
    evas_object_color_get(self->object, &r, &g, &b, &a);
    BENCH_END
    return Py_BuildValue("(iiii)", r, g, b, a);
}


PyObject *
Evas_Object_PyObject_name_set(Evas_Object_PyObject * self, PyObject * args)
{
    char *name;

    if (!PyArg_ParseTuple(args, "s", &name))
        return NULL;

    BENCH_START
    evas_object_name_set(self->object, name);
    BENCH_END
    return Py_INCREF(Py_None), Py_None;
}

PyObject *
Evas_Object_PyObject_name_get(Evas_Object_PyObject * self, PyObject * args)
{
    const char *name;
    BENCH_START
    name = evas_object_name_get(self->object);
    BENCH_END
    return Py_BuildValue("s", name);
}

PyObject *
Evas_Object_PyObject_clip_set(Evas_Object_PyObject * self, PyObject * args)
{
    Evas_Object_PyObject *clip_object;

    if (!PyArg_ParseTuple(args, "O!", &Evas_Object_PyObject_Type, &clip_object))
        return NULL;

    BENCH_START
    evas_object_clip_set(self->object, clip_object->object);
    BENCH_END
    return Py_INCREF(Py_None), Py_None;
}

PyObject *
Evas_Object_PyObject_clip_get(Evas_Object_PyObject * self, PyObject * args)
{
    Evas_PyObject *evas;
    Evas_Object *clip_object;
    
    BENCH_START
    clip_object  = evas_object_clip_get(self->object);
    BENCH_END
    if (!clip_object) {
        Py_INCREF(Py_None);
        return Py_None;
    }

    BENCH_START
    evas = evas_object_data_get(self->object, "evas_pyobject");
    BENCH_END
    return (PyObject *)wrap_evas_object(clip_object, evas);
}


PyObject *
Evas_Object_PyObject_clip_unset(Evas_Object_PyObject * self, PyObject * args)
{
    BENCH_START
    evas_object_clip_unset(self->object);
    BENCH_END
    return Py_INCREF(Py_None), Py_None;
}


PyObject *
Evas_Object_PyObject_clipees_get(Evas_Object_PyObject * self, PyObject * args)
{
    const Evas_List *clipees, *p;
    Evas_PyObject *evas;
    PyObject *list = PyList_New(0);

    BENCH_START 
    evas = evas_object_data_get(self->object, "evas_pyobject");
    clipees = evas_object_clipees_get(self->object);
    BENCH_END

    for (p = clipees; p; p = p->next) {
        Evas_Object *o = (Evas_Object *)p->data;
        PyList_Append(list, (PyObject *)wrap_evas_object(o, evas));
    }
    return list;
}

PyObject *
Evas_Object_PyObject_render_op_set(Evas_Object_PyObject * self, PyObject * args)
{
    int op;

    if (!PyArg_ParseTuple(args, "i", &op))
        return NULL;

    BENCH_START
    evas_object_render_op_set(self->object, op);
    BENCH_END
    return Py_INCREF(Py_None), Py_None;
}

PyObject *
Evas_Object_PyObject_render_op_get(Evas_Object_PyObject * self, PyObject * args)
{
    int op;

    BENCH_START
    op = evas_object_render_op_get(self->object);
    BENCH_END

    return Py_BuildValue("i", op);
}
PyObject *
Evas_Object_PyObject_raise(Evas_Object_PyObject * self, PyObject * args)
{
    BENCH_START
    evas_object_raise(self->object);
    BENCH_END
    return Py_INCREF(Py_None), Py_None;
}

PyObject *
Evas_Object_PyObject_lower(Evas_Object_PyObject * self, PyObject * args)
{
    BENCH_START
    evas_object_lower(self->object);
    BENCH_END
    return Py_INCREF(Py_None), Py_None;
}

PyObject *
Evas_Object_PyObject_stack_above(Evas_Object_PyObject * self, PyObject * args)
{
    Evas_Object_PyObject *above;

    if (!PyArg_ParseTuple(args, "O!", &Evas_Object_PyObject_Type, &above))
        return NULL;

    BENCH_START
    evas_object_stack_above(self->object, above->object);
    BENCH_END
    return Py_INCREF(Py_None), Py_None;
}

PyObject *
Evas_Object_PyObject_stack_below(Evas_Object_PyObject * self, PyObject * args)
{
    Evas_Object_PyObject *below;

    if (!PyArg_ParseTuple(args, "O!", &Evas_Object_PyObject_Type, &below))
        return NULL;

    BENCH_START
    evas_object_stack_below(self->object, below->object);
    BENCH_END
    return Py_INCREF(Py_None), Py_None;
}


/**************************************************************************
 * IMAGE objects
 **************************************************************************/
// *INDENT-OFF*
PyMethodDef Evas_Object_PyObject_methods[] = {
    {"type_get", (PyCFunction) Evas_Object_PyObject_type_get, METH_VARARGS},
    {"move", (PyCFunction) Evas_Object_PyObject_move, METH_VARARGS},
    {"resize", (PyCFunction) Evas_Object_PyObject_resize, METH_VARARGS},
    {"show", (PyCFunction) Evas_Object_PyObject_show, METH_VARARGS},
    {"hide", (PyCFunction) Evas_Object_PyObject_hide, METH_VARARGS},
    {"geometry_get", (PyCFunction) Evas_Object_PyObject_geometry_get, METH_VARARGS},
    {"evas_get", (PyCFunction) Evas_Object_PyObject_evas_get, METH_VARARGS},
    {"layer_set", (PyCFunction) Evas_Object_PyObject_layer_set, METH_VARARGS},
    {"layer_get", (PyCFunction) Evas_Object_PyObject_layer_get, METH_VARARGS},
    {"visible_get", (PyCFunction) Evas_Object_PyObject_visible_get, METH_VARARGS},
    {"color_set", (PyCFunction) Evas_Object_PyObject_color_set, METH_VARARGS},
    {"color_get", (PyCFunction) Evas_Object_PyObject_color_get, METH_VARARGS},
    {"name_set", (PyCFunction) Evas_Object_PyObject_name_set, METH_VARARGS},
    {"name_get", (PyCFunction) Evas_Object_PyObject_name_get, METH_VARARGS},
    {"clip_set", (PyCFunction) Evas_Object_PyObject_clip_set, METH_VARARGS},
    {"clip_get", (PyCFunction) Evas_Object_PyObject_clip_get, METH_VARARGS},
    {"clip_unset", (PyCFunction) Evas_Object_PyObject_clip_unset, METH_VARARGS},
    {"clipees_get", (PyCFunction) Evas_Object_PyObject_clipees_get, METH_VARARGS},
    {"render_op_set", (PyCFunction) Evas_Object_PyObject_render_op_set, METH_VARARGS},
    {"render_op_get", (PyCFunction) Evas_Object_PyObject_render_op_get, METH_VARARGS},

    // stacking
    {"object_raise", (PyCFunction) Evas_Object_PyObject_raise, METH_VARARGS},
    {"object_lower", (PyCFunction) Evas_Object_PyObject_lower, METH_VARARGS},
    {"stack_above", (PyCFunction) Evas_Object_PyObject_stack_above, METH_VARARGS},
    {"stack_below", (PyCFunction) Evas_Object_PyObject_stack_below, METH_VARARGS},
/* TODO:
	above_get / below_get / bottom_get / top_get
	clip_*
	focus_*

	key / events stuff
	callbacks
*/

    // image.c
    {"image_file_set", (PyCFunction) Evas_Object_PyObject_image_file_set, METH_VARARGS},
    {"image_file_get", (PyCFunction) Evas_Object_PyObject_image_file_get, METH_VARARGS},
    {"image_fill_set", (PyCFunction) Evas_Object_PyObject_image_fill_set, METH_VARARGS},
    {"image_fill_get", (PyCFunction) Evas_Object_PyObject_image_fill_get, METH_VARARGS},
    {"image_size_set", (PyCFunction) Evas_Object_PyObject_image_size_set, METH_VARARGS},
    {"image_size_get", (PyCFunction) Evas_Object_PyObject_image_size_get, METH_VARARGS},
    {"image_alpha_set", (PyCFunction) Evas_Object_PyObject_image_alpha_set, METH_VARARGS},
    {"image_alpha_get", (PyCFunction) Evas_Object_PyObject_image_alpha_get, METH_VARARGS},
    {"image_smooth_scale_set", (PyCFunction) Evas_Object_PyObject_image_smooth_scale_set, METH_VARARGS},
    {"image_smooth_scale_get", (PyCFunction) Evas_Object_PyObject_image_smooth_scale_get, METH_VARARGS},
    {"image_data_set", (PyCFunction) Evas_Object_PyObject_image_data_set, METH_VARARGS},
    {"image_data_get", (PyCFunction) Evas_Object_PyObject_image_data_get, METH_VARARGS},
    {"image_data_update_add", (PyCFunction) Evas_Object_PyObject_image_data_update_add, METH_VARARGS},
    {"image_load_error_get", (PyCFunction) Evas_Object_PyObject_image_load_error_get, METH_VARARGS},
    {"image_reload", (PyCFunction) Evas_Object_PyObject_image_reload, METH_VARARGS},
    {"image_pixels_dirty_set", (PyCFunction) Evas_Object_PyObject_image_pixels_dirty_set, METH_VARARGS},
    {"image_pixels_dirty_get", (PyCFunction) Evas_Object_PyObject_image_pixels_dirty_get, METH_VARARGS},
    {"image_pixels_import", (PyCFunction) Evas_Object_PyObject_image_pixels_import, METH_VARARGS},
    {"image_border_set", (PyCFunction) Evas_Object_PyObject_image_border_set, METH_VARARGS},
    {"image_border_get", (PyCFunction) Evas_Object_PyObject_image_border_get, METH_VARARGS},
    {"image_border_center_fill_get", (PyCFunction) Evas_Object_PyObject_image_border_center_fill_get, METH_VARARGS},
    {"image_border_center_fill_set", (PyCFunction) Evas_Object_PyObject_image_border_center_fill_set, METH_VARARGS},

    // text.c
    {"text_font_set", (PyCFunction) Evas_Object_PyObject_text_font_set, METH_VARARGS},
    {"text_font_get", (PyCFunction) Evas_Object_PyObject_text_font_get, METH_VARARGS},
    {"text_text_set", (PyCFunction) Evas_Object_PyObject_text_text_set, METH_VARARGS},
    {"text_text_get", (PyCFunction) Evas_Object_PyObject_text_text_get, METH_VARARGS},
    {"text_font_source_set", (PyCFunction) Evas_Object_PyObject_text_font_source_set, METH_VARARGS},
    {"text_font_source_get", (PyCFunction) Evas_Object_PyObject_text_font_source_get, METH_VARARGS},
    {"text_ascent_get", (PyCFunction) Evas_Object_PyObject_text_ascent_get, METH_VARARGS},
    {"text_descent_get", (PyCFunction) Evas_Object_PyObject_text_descent_get, METH_VARARGS},
    {"text_max_ascent_get", (PyCFunction) Evas_Object_PyObject_text_max_ascent_get, METH_VARARGS},
    {"text_max_descent_get", (PyCFunction) Evas_Object_PyObject_text_max_descent_get, METH_VARARGS},
    {"text_horiz_advance_get", (PyCFunction) Evas_Object_PyObject_text_horiz_advance_get, METH_VARARGS},
    {"text_vert_advance_get", (PyCFunction) Evas_Object_PyObject_text_vert_advance_get, METH_VARARGS},
    {"text_inset_get", (PyCFunction) Evas_Object_PyObject_text_inset_get, METH_VARARGS},
    {"text_char_pos_get", (PyCFunction) Evas_Object_PyObject_text_char_pos_get, METH_VARARGS},
    {"text_char_coords_get", (PyCFunction) Evas_Object_PyObject_text_char_coords_get, METH_VARARGS},
    {"text_style_pad_get", (PyCFunction) Evas_Object_PyObject_text_style_pad_get, METH_VARARGS},

    // textblock.c
    {"textblock_clear", (PyCFunction) Evas_Object_PyObject_textblock_clear, METH_VARARGS},
    {"textblock_style_set", (PyCFunction) Evas_Object_PyObject_textblock_style_set, METH_VARARGS},
    {"textblock_markup_set", (PyCFunction) Evas_Object_PyObject_textblock_markup_set, METH_VARARGS},
    {"textblock_markup_get", (PyCFunction) Evas_Object_PyObject_textblock_markup_get, METH_VARARGS},
    {"textblock_size_formatted_get", (PyCFunction) Evas_Object_PyObject_textblock_size_formatted_get, METH_VARARGS},
    {"textblock_size_native_get", (PyCFunction) Evas_Object_PyObject_textblock_size_native_get, METH_VARARGS},
    {"textblock_style_insets_get", (PyCFunction) Evas_Object_PyObject_textblock_style_insets_get, METH_VARARGS},
    {"textblock_cursor_get", (PyCFunction) Evas_Object_PyObject_textblock_cursor_get, METH_VARARGS},
    {"textblock_line_number_geometry_get", (PyCFunction) Evas_Object_PyObject_textblock_line_number_geometry_get, METH_VARARGS},

    // gradient.c
    {"gradient_color_stop_add", (PyCFunction) Evas_Object_PyObject_gradient_color_stop_add, METH_VARARGS},
    {"gradient_clear", (PyCFunction) Evas_Object_PyObject_gradient_clear, METH_VARARGS},
    {"gradient_angle_set", (PyCFunction) Evas_Object_PyObject_gradient_angle_set, METH_VARARGS},
    {"gradient_angle_get", (PyCFunction) Evas_Object_PyObject_gradient_angle_get, METH_VARARGS},

    {NULL, NULL}
};
// *INDENT-ON*

PyObject *
Evas_Object_PyObject__getattro(Evas_Object_PyObject * self, PyObject *name)
{
    PyObject *attr_value;
    char *sname = PyString_AsString(name);


    attr_value =
        evas_hash_find(evas_object_data_get(self->object, "pyattrs"), sname);
    if (attr_value) {
        Py_INCREF(attr_value);
        return attr_value;
    }

    return PyObject_GenericGetAttr((PyObject *)self, name);
}

int
Evas_Object_PyObject__setattro(Evas_Object_PyObject * self, PyObject *name,
                              PyObject * value)
{
    Evas_Hash *attrs, *orig;
    PyObject *old_value;
    char *sname = PyString_AsString(name);

    //fprintf(stderr, "EVAS OBJECT setattr: %s\n", sname);
    orig = attrs = evas_object_data_get(self->object, "pyattrs");

    old_value = evas_hash_find(attrs, sname);
    if (value == 0)
        attrs = evas_hash_del(attrs, sname, old_value);
    else {
        Py_INCREF(value);
        attrs = evas_hash_add(attrs, sname, value);
        if (!orig)
            evas_object_data_set(self->object, "pyattrs", attrs);
    }
    if (old_value) {
        Py_DECREF(old_value);
    }

    return 0;
}

int
Evas_Object_PyObject__compare(Evas_Object_PyObject *a, Evas_Object_PyObject *b)
{
    return (a->object == b->object) ? 0 : 1;
}


PyTypeObject Evas_Object_PyObject_Type = {
    PyObject_HEAD_INIT(NULL)
    0,                          /* ob_size */
    "_evas.Object",             /* tp_name */
    sizeof(Evas_Object_PyObject),       /* tp_basicsize */
    0,                          /* tp_itemsize */
    (destructor) Evas_Object_PyObject__dealloc,           /* tp_dealloc */
    0,                          /* tp_print */
    0,                          /* tp_getattr */
    0,                          /* tp_setattr */
    (cmpfunc) Evas_Object_PyObject__compare,              /* tp_compare */
    0,                          /* tp_repr */
    0,                          /* tp_as_number */
    0,                          /* tp_as_sequence */
    0,                          /* tp_as_mapping */
    0,                          /* tp_hash */
    0,                          /* tp_call */
    0,                          /* tp_str */
    (getattrofunc) Evas_Object_PyObject__getattro,        /* tp_getattro */
    (setattrofunc) Evas_Object_PyObject__setattro,        /* tp_setattro */
    0,                          /* tp_as_buffer */
    Py_TPFLAGS_DEFAULT | Py_TPFLAGS_BASETYPE | Py_TPFLAGS_HAVE_GC,         /* tp_flags */
    "Evas Object",               /* tp_doc */
    (traverseproc)Evas_Object_PyObject__traverse,   /* tp_traverse */
    (inquiry)Evas_Object_PyObject__clear,           /* tp_clear */
    0,                     /* tp_richcompare */
    0,                     /* tp_weaklistoffset */
    0,                     /* tp_iter */
    0,                     /* tp_iternext */
    Evas_Object_PyObject_methods,  /* tp_methods */
    0,                         /* tp_members */
    0,                         /* tp_getset */
    0,                         /* tp_base */
    0,                         /* tp_dict */
    0,                         /* tp_descr_get */
    0,                         /* tp_descr_set */
    0,                         /* tp_dictoffset */
    (initproc)Evas_Object_PyObject__init,  /* tp_init */
    0,                         /* tp_alloc */
    Evas_Object_PyObject__new, /* tp_new */
};


// vim: ts=4
