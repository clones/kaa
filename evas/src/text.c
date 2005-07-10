#include <Python.h>
#include <Evas.h>

#include "object.h"
#include "text.h"

PyObject *
Evas_Object_PyObject_text_font_set(Evas_Object_PyObject * self, PyObject * args)
{
    char *font;
    int size;

    if (!PyArg_ParseTuple(args, "si", &font, &size))
        return NULL;

    evas_object_text_font_set(self->object, font, size);
    return Py_INCREF(Py_None), Py_None;

}

PyObject *
Evas_Object_PyObject_text_font_get(Evas_Object_PyObject * self, PyObject * args)
{
    char *font;
    int size;

    evas_object_text_font_get(self->object, &font, &size);
    return Py_BuildValue("(si)", font, size);
}

/****************************************************************************/

PyObject *
Evas_Object_PyObject_text_text_set(Evas_Object_PyObject * self, PyObject * args)
{
    char *text;

    if (!PyArg_ParseTuple(args, "s", &text))
        return NULL;

    evas_object_text_text_set(self->object, text);
    return Py_INCREF(Py_None), Py_None;

}

PyObject *
Evas_Object_PyObject_text_text_get(Evas_Object_PyObject * self, PyObject * args)
{
    return Py_BuildValue("s", evas_object_text_text_get(self->object));
}

/****************************************************************************/

PyObject *
Evas_Object_PyObject_text_font_source_set(Evas_Object_PyObject * self,
                                   PyObject * args)
{
    char *source;

    if (!PyArg_ParseTuple(args, "s", &source))
        return NULL;

    evas_object_text_font_source_set(self->object, source);
    return Py_INCREF(Py_None), Py_None;

}

PyObject *
Evas_Object_PyObject_text_font_source_get(Evas_Object_PyObject * self,
                                   PyObject * args)
{
    return Py_BuildValue("s", evas_object_text_font_source_get(self->object));
}

/****************************************************************************
 * METRIC FUNCTIONS
 */

#define func_template(func) \
   PyObject * \
   Evas_Object_PyObject_text_ ## func (Evas_Object_PyObject *self, PyObject *args) \
   { \
      return Py_BuildValue("i", evas_object_text_ ## func (self->object)); \
   }

func_template(ascent_get);
func_template(descent_get);
func_template(max_ascent_get);
func_template(max_descent_get);
func_template(horiz_advance_get);
func_template(vert_advance_get);
func_template(inset_get);

PyObject *
Evas_Object_PyObject_text_char_pos_get(Evas_Object_PyObject * self, PyObject * args)
{
    int pos;
    Evas_Coord cx, cy, cw, ch;

    if (!PyArg_ParseTuple(args, "i", &pos))
        return NULL;

    evas_object_text_char_pos_get(self->object, pos, &cx, &cy, &cw, &ch);
    return Py_BuildValue("(iiii)", cx, cy, cw, ch);
}

PyObject *
Evas_Object_PyObject_text_char_coords_get(Evas_Object_PyObject * self,
                                   PyObject * args)
{
    int x, y;
    Evas_Coord cx, cy, cw, ch;

    if (!PyArg_ParseTuple(args, "ii", &x, &y))
        return NULL;

    evas_object_text_char_coords_get(self->object, x, y, &cx, &cy, &cw, &ch);
    return Py_BuildValue("(iiii)", cx, cy, cw, ch);
}

/****************************************************************************/
