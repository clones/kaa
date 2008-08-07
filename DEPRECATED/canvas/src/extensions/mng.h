/*
 * ----------------------------------------------------------------------------
 * mng.h
 * ----------------------------------------------------------------------------
 * $Id$
 *
 * ----------------------------------------------------------------------------
 * kaa.canvas - Canvas library based on kaa.evas
 * Copyright (C) 2005, 2006 Jason Tackaberry
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

#ifndef _MNG_H_
#define _MNG_H_

#include <libmng.h>
#include <stdint.h>

typedef struct {
    PyObject_HEAD

    uint8_t *mng_data;
    int mng_data_pos, mng_data_len;

    uint8_t *buffer;
    int width, height;

    mng_uint32 frame_delay;
    mng_handle mng;
    PyObject *refresh_callback;
} MNG_PyObject;

extern PyTypeObject MNG_PyObject_Type;
#endif
