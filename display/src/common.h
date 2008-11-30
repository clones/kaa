/*
 * ----------------------------------------------------------------------------
 * common.h
 * ----------------------------------------------------------------------------
 * $Id: common.c 2211 2006-12-10 19:33:58Z tack $
 * ----------------------------------------------------------------------------
 * kaa.display - Generic Display Module
 * Copyright (C) 2005, 2006 Dirk Meyer, Jason Tackaberry
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

void **get_module_api(char *module);

#define CHECK_IMAGE_PYOBJECT \
    if (!Image_PyObject_Type) { \
        PyErr_Format(PyExc_SystemError, "kaa.imlib2 is required but is not available."); \
        return NULL; \
    }
