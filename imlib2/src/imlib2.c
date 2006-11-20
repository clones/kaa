/*
 * ----------------------------------------------------------------------------
 * Imlib2 wrapper for Python
 * ----------------------------------------------------------------------------
 * $Id$
 *
 * ----------------------------------------------------------------------------
 * kaa.imlib2 - An imlib2 wrapper for Python
 * Copyright (C) 2004-2006 Jason Tackaberry <tack@sault.org>
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

#include "config.h"

#include <Python.h>
#define X_DISPLAY_MISSING
#include <Imlib2.h>
#include <errno.h>

#include <fcntl.h>
#ifdef HAVE_POSIX_SHMEM
#include <sys/mman.h>
#endif

#include "image.h"
#include "rawformats.h"
#include "font.h"

PyObject *imlib2_create(PyObject *self, PyObject *args)
{
    int w, h, len, copy;
    void *bytes = NULL;
	char *from_format = "BGRA";
    PyObject *data = NULL;
    Imlib_Image *image = NULL;
    Image_PyObject *o;

    if (!PyArg_ParseTuple(args, "(ii)|Osi", &w, &h, &data, &from_format, &copy))
        return NULL;

    if (strcmp(from_format, "BGRA") && !copy) {
        PyErr_Format(PyExc_ValueError, "Non-BGRA format must use copy = True");
        return NULL;
    }

    if (data) {
        if (PyNumber_Check(data)) {
            bytes = (void *)PyLong_AsLong(data);
            data = NULL;
        }
        else {
            int r = PyObject_AsWriteBuffer(data, &bytes, &len);
            if (r == -1) {
                // Write buffer failed.  If we weren't asked to copy, we need
                // to raise an exception.
                if (!copy) {
                    PyErr_Format(PyExc_ValueError, "Read-only buffer given, but copy = False");
                    return NULL;
                }
                PyErr_Clear();
                if (PyObject_AsReadBuffer(data, (const void **)&bytes, &len) == -1)
                    return NULL;
                data = NULL;
            }
        }

        if (!strcmp(from_format, "BGRA")) {
            if (copy)
                image = imlib_create_image_using_copied_data(w, h, bytes);
            else
                image = imlib_create_image_using_data(w, h, bytes);
        } else {
            bytes = (void *)convert_raw_rgba_bytes(from_format, "BGRA", bytes, NULL, w, h);
            image = imlib_create_image_using_copied_data(w, h, bytes);
            free(bytes);
        }
        imlib_context_set_image(image);
        if (strlen(from_format) == 4)
            imlib_image_set_has_alpha(1);
    } else {
        image = imlib_create_image(w, h);
        imlib_context_set_image(image);
        imlib_image_set_has_alpha(1);
        imlib_image_clear_color(0, 0, 0, 0);
    }
    if (!image) {
        PyErr_Format(PyExc_RuntimeError, "Failed to create image");
        return NULL;
    }

    o = PyObject_NEW(Image_PyObject, &Image_PyObject_Type);
    o->image = image;
    o->buffer = o->raw_data = NULL;
    if (!copy && data) {
        o->buffer = data;
        Py_INCREF(o->buffer);
    }
    return (PyObject *)o;
}

static
Image_PyObject *_imlib2_open(char *filename, int use_cache)
{
    Imlib_Image *image;
    Image_PyObject *o;
    Imlib_Load_Error error_return = IMLIB_LOAD_ERROR_NONE;

    if (use_cache)
      image = imlib_load_image_with_error_return(filename, &error_return);
    else
      image = imlib_load_image_immediately_without_cache(filename);

    if (!image) {
        if (error_return == IMLIB_LOAD_ERROR_NO_LOADER_FOR_FILE_FORMAT)
            PyErr_Format(PyExc_IOError, "no loader for file format");
        else
            PyErr_Format(PyExc_IOError, "Could not open %s: %d", filename,
	    	     error_return);
        return NULL;
    }
    o = PyObject_NEW(Image_PyObject, &Image_PyObject_Type);
    o->image = image;
    o->buffer = o->raw_data = NULL;
    return o;
}

PyObject *imlib2_open(PyObject *self, PyObject *args)
{
    char *file;
    Image_PyObject *image;
    int use_cache = 1;

    if (!PyArg_ParseTuple(args, "s|i", &file, &use_cache))
        return NULL;

    image = _imlib2_open(file, use_cache);
    if (!image)
        return NULL;
    return (PyObject *)image;
}

PyObject *imlib2_open_from_memory(PyObject *self, PyObject *args)
{
    Image_PyObject *image = NULL;
    PyObject *buffer;
    void *data;
    int len, fd;
    static int prng_seeded = 0;
    char filename[30], path[PATH_MAX];

    if (!PyArg_ParseTuple(args, "O!", &PyBuffer_Type, &buffer))
        return NULL;

    PyObject_AsReadBuffer(buffer, (const void **)&data, &len);

    // Seed PRNG for generating sufficiently unique filenames.  We only need
    // a filename which is extremely unlikely to exist.  Files are opened with
    // O_EXCL so this code should not be vulnerable to symlink attacks.  (It
    // will fail, but won't leak data to the attacker.)
    if (!prng_seeded) {
        prng_seeded = 1;
        srand((unsigned int)time(0)*getpid());
    }
    snprintf(filename, sizeof(filename), "kaa-imlib2-img-%d", rand());

#ifdef HAVE_POSIX_SHMEM
    // Faster to use shared memory, if available ...
    snprintf(path, sizeof(path), "/dev/shm/%s", filename);
    fd = shm_open(filename, O_RDWR | O_CREAT | O_EXCL, 0600);
    if (fd != -1) {
        int write_success = write(fd, data, len) == len;
        close(fd);
        if (write_success)
            image = _imlib2_open(path, 0);
        shm_unlink(filename);
        if (image)
            return (PyObject *)image;
    }
    // Shmem failed, fall back to file system.  Clear any exception raised above.
    PyErr_Clear();
#endif
    snprintf(path, sizeof(path), "/tmp/kaa-%d/%s", getuid(), filename);
    fd = open(path, O_RDWR | O_CREAT | O_EXCL, 0600);
    if (fd == -1) {
        PyErr_Format(PyExc_IOError, "Unable to save temporary file '%s': %s", path, strerror(errno));
        return NULL;
    }
    if (write(fd, data, len) == len)
        image = _imlib2_open(path, 0);
    close(fd);
    unlink(path);

    if (!image) {
        if (!PyErr_Occurred())
            PyErr_Format(PyExc_IOError, "Failed writing to temporary file '%s': %s", path, strerror(errno));
        return NULL;
    }

    return (PyObject *)image;
}

PyObject *imlib2_add_font_path(PyObject *self, PyObject *args)
{
    char *font_path;

    if (!PyArg_ParseTuple(args, "s", &font_path))
        return NULL;

    imlib_add_path_to_font_path(font_path);
    Py_INCREF(Py_None);
    return Py_None;
}


PyObject *imlib2_load_font(PyObject *self, PyObject *args)
{
    char *font_spec;
    Imlib_Font *font;
    Font_PyObject *o;

    if (!PyArg_ParseTuple(args, "s", &font_spec))
        return NULL;

    font = imlib_load_font(font_spec);
    if (!font) {
        PyErr_Format(PyExc_IOError, "Couldn't open font: %s", font_spec);
        return NULL;
    }
    o = PyObject_NEW(Font_PyObject, &Font_PyObject_Type);
    o->font = font;
    return (PyObject *)o;
}


PyMethodDef Imlib2_methods[] = {
    { "add_font_path", imlib2_add_font_path, METH_VARARGS },
    { "load_font", imlib2_load_font, METH_VARARGS },
    { "create", imlib2_create, METH_VARARGS },
    { "open", imlib2_open, METH_VARARGS },
    { "open_from_memory", imlib2_open_from_memory, METH_VARARGS },
    { NULL }
};


void init_Imlib2()
{
    PyObject *m, *c_api;
    static void *api_ptrs[2];

    m = Py_InitModule("_Imlib2", Imlib2_methods);
    Image_PyObject_Type.tp_new = PyType_GenericNew;
    if (PyType_Ready(&Image_PyObject_Type) < 0)
        return;
    PyModule_AddObject(m, "Image", (PyObject *)&Image_PyObject_Type);
    imlib_set_cache_size(1024*1024*4);
    imlib_set_font_cache_size(1024*1024*2);

    // Export a simple API for other extension modules to be able to access
    // and manipulate Image objects.
    api_ptrs[0] = (void *)imlib_image_from_pyobject;
    api_ptrs[1] = (void *)&Image_PyObject_Type;
    c_api = PyCObject_FromVoidPtr((void *)api_ptrs, NULL);
    PyModule_AddObject(m, "_C_API", c_api);
}
