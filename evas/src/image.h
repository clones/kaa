/*
 * ----------------------------------------------------------------------------
 * image.h - image evas object wrapper
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

void *get_ptr_from_pyobject(PyObject *o, int *len);

PyObject *Evas_Object_PyObject_image_file_set(Evas_Object_PyObject *, PyObject *);
PyObject *Evas_Object_PyObject_image_file_get(Evas_Object_PyObject *, PyObject *);

PyObject *Evas_Object_PyObject_image_fill_set(Evas_Object_PyObject *, PyObject *);
PyObject *Evas_Object_PyObject_image_fill_get(Evas_Object_PyObject *, PyObject *);

PyObject *Evas_Object_PyObject_image_border_set(Evas_Object_PyObject *, PyObject *);
PyObject *Evas_Object_PyObject_image_border_get(Evas_Object_PyObject *, PyObject *);
PyObject *Evas_Object_PyObject_image_border_center_fill_set(Evas_Object_PyObject *, PyObject *);
PyObject *Evas_Object_PyObject_image_border_center_fill_get(Evas_Object_PyObject *, PyObject *);

PyObject *Evas_Object_PyObject_image_size_set(Evas_Object_PyObject *, PyObject *);
PyObject *Evas_Object_PyObject_image_size_get(Evas_Object_PyObject *, PyObject *);

PyObject *Evas_Object_PyObject_image_alpha_set(Evas_Object_PyObject *, PyObject *);
PyObject *Evas_Object_PyObject_image_alpha_get(Evas_Object_PyObject *, PyObject *);

PyObject *Evas_Object_PyObject_image_smooth_scale_set(Evas_Object_PyObject *, PyObject *);
PyObject *Evas_Object_PyObject_image_smooth_scale_get(Evas_Object_PyObject *, PyObject *);

PyObject *Evas_Object_PyObject_image_data_set(Evas_Object_PyObject *, PyObject *, PyObject *);
PyObject *Evas_Object_PyObject_image_data_get(Evas_Object_PyObject *, PyObject *);
PyObject *Evas_Object_PyObject_image_data_update_add(Evas_Object_PyObject *, PyObject *);

PyObject *Evas_Object_PyObject_image_load_error_get(Evas_Object_PyObject *, PyObject *);
PyObject *Evas_Object_PyObject_image_reload(Evas_Object_PyObject *, PyObject *);

PyObject *Evas_Object_PyObject_image_pixels_dirty_set(Evas_Object_PyObject *, PyObject *);
PyObject *Evas_Object_PyObject_image_pixels_dirty_get(Evas_Object_PyObject *, PyObject *);
PyObject *Evas_Object_PyObject_image_pixels_import(Evas_Object_PyObject *, PyObject *, PyObject *);
PyObject *Evas_Object_PyObject_image_colorspace_set(Evas_Object_PyObject *, PyObject *);
PyObject *Evas_Object_PyObject_image_colorspace_get(Evas_Object_PyObject *, PyObject *);

