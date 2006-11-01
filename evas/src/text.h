/*
 * ----------------------------------------------------------------------------
 * text.h - evas text object wrapper
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

PyObject *Evas_Object_PyObject_text_font_set(Evas_Object_PyObject *, PyObject *);
PyObject *Evas_Object_PyObject_text_font_get(Evas_Object_PyObject *, PyObject *);

PyObject *Evas_Object_PyObject_text_text_set(Evas_Object_PyObject *, PyObject *);
PyObject *Evas_Object_PyObject_text_text_get(Evas_Object_PyObject *, PyObject *);

PyObject *Evas_Object_PyObject_text_font_source_set(Evas_Object_PyObject *, PyObject *);
PyObject *Evas_Object_PyObject_text_font_source_get(Evas_Object_PyObject *, PyObject *);

// metrics
PyObject *Evas_Object_PyObject_text_ascent_get(Evas_Object_PyObject *, PyObject *);
PyObject *Evas_Object_PyObject_text_descent_get(Evas_Object_PyObject *, PyObject *);
PyObject *Evas_Object_PyObject_text_max_ascent_get(Evas_Object_PyObject *, PyObject *);
PyObject *Evas_Object_PyObject_text_max_descent_get(Evas_Object_PyObject *, PyObject *);
PyObject *Evas_Object_PyObject_text_horiz_advance_get(Evas_Object_PyObject *, PyObject *);
PyObject *Evas_Object_PyObject_text_vert_advance_get(Evas_Object_PyObject *, PyObject *);
PyObject *Evas_Object_PyObject_text_inset_get(Evas_Object_PyObject *, PyObject *);
PyObject *Evas_Object_PyObject_text_char_pos_get(Evas_Object_PyObject *, PyObject *);
PyObject *Evas_Object_PyObject_text_char_coords_get(Evas_Object_PyObject *, PyObject *);
PyObject *Evas_Object_PyObject_text_style_pad_get(Evas_Object_PyObject *, PyObject *);
