#include "engine_buffer.h"
#include <Evas_Engine_Buffer.h>

PyObject *engine_buffer_setup(Evas_PyObject *o, PyObject *kwargs)
{
    Evas_Engine_Info_Buffer *einfo;
    int buflen, w, h;
    PyObject *value, *buffer;

    BENCH_START
    evas_output_method_set(o->evas, evas_render_method_lookup("buffer"));
    BENCH_END

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
    if (!value || value == Py_None) {
        buffer = PyBuffer_New(einfo->info.dest_buffer_row_bytes * h);
        if (PyObject_AsWriteBuffer(buffer, &einfo->info.dest_buffer, &buflen) == -1)
            return 0;
    } else {
        if (PyNumber_Check(value)) {
            einfo->info.dest_buffer = (void *) PyLong_AsLong(value);
            buffer = PyBuffer_FromReadWriteMemory(einfo->info.dest_buffer, 
                                                  einfo->info.dest_buffer_row_bytes * h);
        } else {
            if (PyObject_AsWriteBuffer(value, &einfo->info.dest_buffer, &buflen) == -1)
                return 0;
            if (buflen < einfo->info.dest_buffer_row_bytes * h) {
                PyErr_SetString(PyExc_AttributeError, "Buffer not big enough");
                return 0;
            }
            buffer = value;
            Py_INCREF(buffer);
        }
    }

    BENCH_START
    evas_engine_info_set(o->evas, (Evas_Engine_Info *) einfo);
    BENCH_END
    return buffer;
}
