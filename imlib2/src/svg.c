/*
 * ----------------------------------------------------------------------------
 * Imlib2 wrapper for Python
 * ----------------------------------------------------------------------------
 * $Id: font.c 2940 2008-01-05 19:35:46Z tack $
 *
 * ----------------------------------------------------------------------------
 * kaa.imlib2 - An imlib2 wrapper for Python
 * Copyright (C) 2005 Jason Tackaberry <tack@urandom.ca>
 *
 * First Edition: Jason Tackaberry <tack@urandom.ca>
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
    int w, h;
    Py_ssize_t len;
    guchar *svgdata;

    GError *error = NULL;
    RsvgHandle *svg;
    GdkPixbuf *pixbuf;
    gboolean res;
    size_cb_data cbdata;

    PyObject *buffer;
    guchar *buffer_ptr;
    
    if (!PyArg_ParseTuple(args, "iis#", &w, &h, &svgdata, &len))
        return NULL;

    cbdata.w = w;
    cbdata.h = h;

    svg = rsvg_handle_new();
    if ( w && h )
        rsvg_handle_set_size_callback(svg, size_cb, &cbdata, NULL);
    res = rsvg_handle_write(svg, svgdata, len, &error);
    if (error != NULL)         {
        PyErr_Format(PyExc_RuntimeError, "SVG Error: %s", error->message);
        g_error_free (error);
        return NULL;
    }
    
    res = rsvg_handle_close(svg, &error);
    if (error != NULL) {
        PyErr_Format(PyExc_RuntimeError, "SVG Error: %s", error->message);
        g_error_free (error);
        return NULL;
    }

    pixbuf = rsvg_handle_get_pixbuf(svg);

    w = gdk_pixbuf_get_width(pixbuf);
    h = gdk_pixbuf_get_height(pixbuf);

    buffer = PyBuffer_New(w*h*4);
    PyObject_AsWriteBuffer(buffer, (void **)&buffer_ptr, &len);
    memcpy(buffer_ptr, gdk_pixbuf_get_pixels(pixbuf), w*h*4);
    rsvg_handle_free(svg);
    g_object_unref(pixbuf);

    return Py_BuildValue("(iiO)", w, h, buffer);
}
