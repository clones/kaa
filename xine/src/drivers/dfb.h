/* -*- coding: iso-8859-1 -*-
 * ----------------------------------------------------------------------------
 * dfb.h - DirectFB Driver
 * ----------------------------------------------------------------------------
 * $Id: $
 *
 * ----------------------------------------------------------------------------
 * kaa-xine - Xine wrapper
 * Copyright (C) 2005 Jason Tackaberry
 *
 * First Edition: Rob Shortt <rob@tvcentric.com>
 * Maintainer:    Rob Shortt <rob@tvcentric.com>
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
 * ------------------------------------------------------------------------- */

#ifndef _DFB_H_
#define _DFB_H_

#include <Python.h>
#include "../xine.h"
#include "common.h"


typedef struct _dfb_vo_user_data {
    driver_info_common common;
} dfb_vo_user_data;

int dfb_get_visual_info(Xine_PyObject *xine, PyObject *kwargs, void **visual_return, 
                        driver_info_common **driver_info_return);

#endif
