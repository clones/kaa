/*
 * ----------------------------------------------------------------------------
 * svg.c
 * ----------------------------------------------------------------------------
 * $Id: svg.c 979 2005-12-14 16:09:02Z tack $
 *
 * ----------------------------------------------------------------------------
 * kaa-canvas - Canvas module
 * Copyright (C) 2005 Jason Tackaberry
 *
 * First Edition: Jason Tackaberry <tack@sault.org>
 * Maintainer:    Jason Tackaberry <tack@sault.org>
 *
 * Please see the file doc/CREDITS for a complete list of authors.
 *
 * This program is free software; you can redistribute it and/or modify
 * it under the terms of the GNU General Public License as published by
 * the Free Software Foundation; either version 2 of the License, or
 * (at your option) any later version.
 *
 * This program is distributed in the hope that it will be useful, but
 * WITHOUT ANY WARRANTY; without even the implied warranty of MER-
 * CHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the GNU General
 * Public License for more details.
 *
 * You should have received a copy of the GNU General Public License along
 * with this program; if not, write to the Free Software Foundation, Inc.,
 * 59 Temple Place, Suite 330, Boston, MA 02111-1307 USA
 *
 * ----------------------------------------------------------------------------
 */
#include <Python.h>
#include <librsvg/rsvg.h>

typedef struct _size_cb_data {
    int w, h;
} size_cb_data;

void size_cb(gint *width, gint *height, gpointer user_data)
{
    size_cb_data *data = (size_cb_data *)user_data;
    double aspect = (double)*width / *height;
    if (data->w <= 0 && data->h <= 0)
        return;
    if (data->h <= 0) {
        *width = data->w;
        *height = (int)(data->w / aspect);
    } else if (data->w <= 0) {
        *height = data->h;
        *width = (int)(data->h * aspect);
    } else {
        *width = data->w;
        *height = data->h;
    }
}


PyObject *
render_svg_to_buffer(PyObject *module, PyObject *args, PyObject *kwargs)
{
    int len, w, h, i;
    guchar *svgdata;

    GError *error;
    RsvgHandle *svg;
    GdkPixbuf *pixbuf;
    gboolean res;
    size_cb_data cbdata;

    PyObject *buffer;
    guchar *buffer_ptr, *pixbuf_ptr;
    
    if (!PyArg_ParseTuple(args, "iis#", &w, &h, &svgdata, &len))
        return NULL;

    cbdata.w = w;
    cbdata.h = h;

    svg = rsvg_handle_new();
    rsvg_handle_set_size_callback(svg, size_cb, &cbdata, NULL);
    res = rsvg_handle_write(svg, svgdata, len, &error);
    res = rsvg_handle_close(svg, &error);
    pixbuf = rsvg_handle_get_pixbuf(svg);
    rsvg_handle_free(svg);

    w = gdk_pixbuf_get_width(pixbuf);
    h = gdk_pixbuf_get_height(pixbuf);

    buffer = PyBuffer_New(w*h*4);
    PyObject_AsWriteBuffer(buffer, (void **)&buffer_ptr, &len);
    memcpy(buffer_ptr, gdk_pixbuf_get_pixels(pixbuf), w*h*4);

    // RGBA to BGRA conversion.
    // FIXME: MMXify.
    for (i = 0; i < w*h*4; i+=4) {
        guchar save = buffer_ptr[i+2];
        buffer_ptr[i+2] = buffer_ptr[i];
        buffer_ptr[i] = save;
    }
    return Py_BuildValue("(iiO)", w, h, buffer);
}
   

PyMethodDef svg_methods[] = {
    { "render_svg_to_buffer", ( PyCFunction ) render_svg_to_buffer, METH_VARARGS },
    { NULL }
};

void init_svg()
{
    PyObject *m;
    g_type_init();
    m =  Py_InitModule("_svg", svg_methods);
}
