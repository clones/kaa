/*
 * ----------------------------------------------------------------------------
 * Imlib2 wrapper for Python
 * ----------------------------------------------------------------------------
 * $Id$
 *
 * ----------------------------------------------------------------------------
 * kaa.imlib2 - An imlib2 wrapper for Python
 * Copyright (C) 2004-2006 Jason Tackaberry <tack@urandom.ca>
 *
 * First Edition: Jason Tackaberry <tack@urandom.ca>
 * Maintainer:    Jason Tackaberry <tack@urandom.ca>
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

#define Image_PyObject_Check(v) ((v)->ob_type == &Image_PyObject_Type)

typedef struct {
    PyObject_HEAD
    Imlib_Image *image;
    void *raw_data;
    PyObject *buffer;
} Image_PyObject;

extern PyTypeObject Image_PyObject_Type;
void Image_PyObject__dealloc(Image_PyObject *);
PyObject *Image_PyObject__getattr(Image_PyObject *, char *);

// Exported
Imlib_Image *imlib_image_from_pyobject(Image_PyObject *pyimg);

