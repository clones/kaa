/*
 * ----------------------------------------------------------------------------
 * mng.h
 * ----------------------------------------------------------------------------
 * $Id$
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
