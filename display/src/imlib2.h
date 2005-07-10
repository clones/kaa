/*
 * ----------------------------------------------------------------------------
 * imlib2.h - Imlib2 based X11 display
 * ----------------------------------------------------------------------------
 * $Id$
 *
 * ----------------------------------------------------------------------------
 * kaa-display - X11/SDL Display module
 * Copyright (C) 2005 Dirk Meyer, Jason Tackaberry
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

#ifndef _IMLIB2_H_
#define _IMLIB2_H_

#include "config.h"
#include "display.h"

#ifndef USE_IMLIB2_DISPLAY
    #define X_DISPLAY_MISSING
#else
    #include <X11/Xlib.h>
#endif

#include <Imlib2.h>
extern Imlib_Image *(*imlib_image_from_pyobject)(PyObject *pyimg);

#endif

PyObject *render_imlib2_image(PyObject *self, PyObject *args);

