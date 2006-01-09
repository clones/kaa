#include <Python.h>
#include <Evas.h>

#define Evas_Textblock_Cursor_PyObject_Check(v) ((v)->ob_type == &Evas_Textblock_Cursor_PyObject_Type)

typedef struct {
    PyObject_HEAD
    Evas_Textblock_Cursor *cursor;
    Evas_Object_PyObject *textblock;
} Evas_Textblock_Cursor_PyObject;

extern PyTypeObject Evas_Textblock_Cursor_PyObject_Type;

Evas_Textblock_Cursor_PyObject *wrap_evas_textblock_cursor(Evas_Textblock_Cursor *, Evas_Object_PyObject *);

PyObject *Evas_Object_PyObject_textblock_clear(Evas_Object_PyObject *, PyObject *);
PyObject *Evas_Object_PyObject_textblock_style_set(Evas_Object_PyObject *, PyObject *);
PyObject *Evas_Object_PyObject_textblock_markup_set(Evas_Object_PyObject *, PyObject *);
PyObject *Evas_Object_PyObject_textblock_markup_get(Evas_Object_PyObject *, PyObject *);
PyObject *Evas_Object_PyObject_textblock_size_formatted_get(Evas_Object_PyObject *, PyObject *);
PyObject *Evas_Object_PyObject_textblock_size_native_get(Evas_Object_PyObject *, PyObject *);
PyObject *Evas_Object_PyObject_textblock_style_insets_get(Evas_Object_PyObject *, PyObject *);
PyObject *Evas_Object_PyObject_textblock_cursor_get(Evas_Object_PyObject *, PyObject *);
PyObject *Evas_Object_PyObject_textblock_line_number_geometry_get(Evas_Object_PyObject *, PyObject *);
