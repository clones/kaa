/*
 * ----------------------------------------------------------------------------
 * Thumbnail module for Python
 * ----------------------------------------------------------------------------
 * $Id$
 *
 * ----------------------------------------------------------------------------
 * kaa.beacon - A virtual filesystem with metadata
 * Copyright (C) 2006 Dirk Meyer
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
#include "config.h"

#define X_DISPLAY_MISSING
#include <Imlib2.h>

#ifdef USE_EPEG
#include "Epeg.h"
#endif

#include <sys/types.h>
#include <sys/stat.h>
#include <fcntl.h>

/* kaa.imlib2 usage */
Imlib_Image *(*imlib_image_from_pyobject)(PyObject *pyimg);
PyTypeObject *Image_PyObject_Type;


/* png write function stolen from epsilon (see png.c) */
extern int _png_write (const char *file, DATA32 * ptr,
                       int tw, int th, int sw, int sh, char *imformat,
                       int mtime, char *uri);

PyObject *epeg_thumbnail(PyObject *self, PyObject *args)
{
#ifdef USE_EPEG
    int iw, ih, tw, th, ret;
    char *source;
    char *dest;

    Epeg_Image *im;

    if (!PyArg_ParseTuple(args, "ss(ii)", &source, &dest, &tw, &th))
        return NULL;

    im = epeg_file_open(source);
    if (im) {
        epeg_size_get(im, &iw, &ih);

        if (iw > tw || ih > th) {
            if (iw / tw > ih / th)
                th = (ih * tw) / iw;
            else
                tw = (iw * th) / ih;
        } else {
            tw = iw;
            th = ih;
        }

        epeg_decode_size_set(im, tw, th);
        epeg_quality_set(im, 80);
        epeg_thumbnail_comments_enable(im, 1);

        epeg_file_output_set(im, dest);
        ret = epeg_encode (im);

        if (!ret) {
            epeg_close(im);
            Py_INCREF(Py_None);
            return Py_None;
        }

        epeg_close(im);
        PyErr_SetString(PyExc_IOError, "epeg failed");
    } else
        PyErr_SetString(PyExc_IOError, "epeg failed");

#else
    PyErr_SetString(PyExc_IOError, "epeg support missing");
#endif
    return NULL;
}

PyObject *png_thumbnail(PyObject *self, PyObject *args)
{
    int iw, ih, tw, th;
    char *source;
    char *dest;

    int mtime;
    char uri[PATH_MAX];
    char format[32];
    struct stat filestatus;
    Imlib_Image tmp = NULL;
    Imlib_Image src = NULL;
    PyObject *pyimg = NULL;

    if (!PyArg_ParseTuple(args, "ss(ii)|O!", &source, &dest, &tw, &th,
			  Image_PyObject_Type, &pyimg))
        return NULL;

    if (stat (source, &filestatus) != 0) {
        PyErr_SetString(PyExc_ValueError, "thumbnail: no such file");
        return NULL;
    }

    mtime = filestatus.st_mtime;

    if (!pyimg) {
	/* load source file */
	if (!(tmp = imlib_load_image_immediately_without_cache (source))) {
	    PyErr_SetString(PyExc_ValueError, "imlib2: unable to load image");
	    return NULL;
	}
    } else {
	/* extract from kaa.imlib2 object */
	tmp = imlib_image_from_pyobject(pyimg);
    }

    imlib_context_set_image (tmp);
    snprintf (format, 32, "image/%s", imlib_image_format ());
    iw = imlib_image_get_width ();
    ih = imlib_image_get_height ();
    if (iw > tw || ih > th) {
	if (iw / tw > ih / th) {
	    th = (ih * tw) / iw;
	    if (!th)
		th = 1;
	} else {
	    tw = (iw * th) / ih;
	    if (!tw)
		tw = 1;
	}

	/* scale image down to thumbnail size */
	imlib_context_set_cliprect (0, 0, tw, th);
	src = imlib_create_cropped_scaled_image (0, 0, iw, ih, tw, th);
	if (!src) {
	    if (!pyimg)
		imlib_free_image_and_decache ();
	    PyErr_SetString(PyExc_IOError, "imlib2 scale error");
	    return NULL;
	}
	/* free original image and set context to new one */
        if (!pyimg)
	    imlib_free_image_and_decache ();
	imlib_context_set_image (src);
	pyimg = NULL;
    } else {
	tw = iw;
	th = ih;
    }

    imlib_image_set_has_alpha (1);
    imlib_image_set_format ("argb");
    snprintf (uri, PATH_MAX, "file://%s", source);
    if (_png_write (dest, imlib_image_get_data (), tw, th, iw, ih,
		    format, mtime, uri)) {
        if (!pyimg)
	    imlib_free_image_and_decache ();
	Py_INCREF(Py_None);
	return Py_None;
    }

    if (!pyimg)
	imlib_free_image_and_decache ();
    PyErr_SetString(PyExc_ValueError, "imlib2: unable to save image");
    return NULL;
}


PyObject *fail_thumbnail(PyObject *self, PyObject *args)
{
    Imlib_Image image = NULL;
    char uri[PATH_MAX];
    char *source;
    char *dest;
    char format[32];
    int mtime;
    struct stat filestatus;

    if (!PyArg_ParseTuple(args, "ss", &source, &dest))
        return NULL;

    image = imlib_create_image(1, 1);
    imlib_context_set_image(image);
    imlib_image_set_has_alpha(1);
    imlib_image_clear_color(0, 0, 0, 0);

    if (stat (source, &filestatus) != 0)
	mtime = 0;
    else
	mtime = filestatus.st_mtime;


    mtime = filestatus.st_mtime;

    snprintf (uri, PATH_MAX, "file://%s", source);
    snprintf (format, 32, "image/%s", imlib_image_format ());

    if (_png_write (dest, imlib_image_get_data (), 1, 1, 1, 1,
		    format, mtime, uri)) {
        imlib_free_image_and_decache ();
	Py_INCREF(Py_None);
	return Py_None;
    }
    imlib_free_image_and_decache ();
    PyErr_SetString(PyExc_ValueError, "imlib2: unable to save image");
    return NULL;
}


PyMethodDef thumbnail_methods[] = {
    { "epeg", epeg_thumbnail, METH_VARARGS },
    { "png", png_thumbnail, METH_VARARGS },
    { "failed", fail_thumbnail, METH_VARARGS },
    { NULL }
};


void **get_module_api(char *module)
{
    PyObject *m, *c_api;
    void **ptrs;

    m = PyImport_ImportModule(module);
    if (m == NULL)
       return NULL;
    c_api = PyObject_GetAttrString(m, "_C_API");
    if (c_api == NULL || !PyCObject_Check(c_api))
        return NULL;
    ptrs = (void **)PyCObject_AsVoidPtr(c_api);
    Py_DECREF(c_api);
    return ptrs;
}


void init_libthumb()
{
    PyObject *m;
    void **imlib2_api_ptrs;

    m = Py_InitModule("_libthumb", thumbnail_methods);

    // Import kaa-imlib2's C api
    imlib2_api_ptrs = get_module_api("kaa.imlib2._Imlib2");
    if (imlib2_api_ptrs == NULL)
        return;
    imlib_image_from_pyobject = imlib2_api_ptrs[0];
    Image_PyObject_Type = imlib2_api_ptrs[1];
}
