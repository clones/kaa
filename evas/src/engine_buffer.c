#include "engine_buffer.h"
#include <Evas_Engine_Buffer.h>

int engine_buffer_setup(Evas_PyObject *o, PyObject *kwargs)
{
    Evas_Engine_Info_Buffer *einfo;
    int res, buflen, w, h;
    PyObject *value;

    evas_output_method_set(o->evas, evas_render_method_lookup("buffer"));

    einfo = (Evas_Engine_Info_Buffer *) evas_engine_info_get(o->evas);
    einfo->info.func.new_update_region = NULL;
    einfo->info.func.free_update_region = NULL;
    einfo->info.use_color_key = 0;
    einfo->info.alpha_threshold = 0;

    // Class wrapper ensures these kwargs exist.
    if (!PyArg_ParseTuple(PyDict_GetItemString(kwargs, "size"), "ii", &w, &h))
        return 0;

    einfo->info.depth_type = PyLong_AsLong(PyDict_GetItemString(kwargs, "depth"));
    einfo->info.dest_buffer_row_bytes = PyLong_AsLong(PyDict_GetItemString(kwargs, "stride"));
    einfo->info.dest_buffer = 0;
    value = PyDict_GetItemString(kwargs, "buffer");
    if (PyNumber_Check(value))
        einfo->info.dest_buffer = (void *) PyLong_AsLong(value);
    else {
        res = PyObject_AsWriteBuffer(value, &einfo->info.dest_buffer, &buflen);
        if (res == -1)
            return 0;
        if (buflen < einfo->info.dest_buffer_row_bytes * h) {
            PyErr_SetString(PyExc_AttributeError, "Buffer not big enough");
            return 0;
        }
    }
    evas_engine_info_set(o->evas, (Evas_Engine_Info *) einfo);
    return 1;
}
