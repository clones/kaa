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

#define X_DISPLAY_MISSING
#include <Imlib2.h>
#include <string.h>
#include <stdlib.h>

// XXX: Caller of these functions is responsible for holding global mutex.

unsigned int get_format_bpp(char *format)
{
    if (strstr(format, "24"))
        return 3;
    else if (strstr(format, "32"))
        return 4;
    else
        return strlen(format);
}

unsigned int get_raw_bytes_size(char *format)
{
    unsigned int w = imlib_image_get_width();
    unsigned int h = imlib_image_get_height();

    return w * h * get_format_bpp(format);
}



unsigned char* convert_raw_rgba_bytes(char *from_format, char *to_format,
                                      unsigned char *from_buf, unsigned char *to_buf,
                                      int w, int h)
{
    int from_bpp, to_bpp, i;
    unsigned char fr, fb, fg, fa, tr, tb, tg, ta, *from_ptr, *to_ptr;
    from_bpp = get_format_bpp(from_format);
    to_bpp = get_format_bpp(to_format);

    if (to_buf == 0)
        to_buf = (unsigned char *)malloc(w*h*to_bpp);

#define LOOP_START \
    for (from_ptr = from_buf, to_ptr = to_buf; from_ptr < from_buf + \
           w*h*from_bpp; from_ptr += from_bpp)


    // FIXME: pointless code duplication follows.

    /* Hard code the common cases of BGRA -> RGB/A.  This is pretty much
     * as fast as memcpy.  I don't think it gets much faster without
     * MMX.
     */
    if (!strcmp(from_format, "BGRA") && !strcmp(to_format, "RGB")) {
        LOOP_START {
            *(to_ptr++) = *(from_ptr + 2); *(to_ptr++) = *(from_ptr + 1);
            *(to_ptr++) = *(from_ptr + 0);
        }
    return to_buf;
    }
    if (!strcmp(from_format, "BGRA") && !strcmp(to_format, "RGBA")) {
        LOOP_START {
            *(to_ptr++) = *(from_ptr + 2); *(to_ptr++) = *(from_ptr + 1);
            *(to_ptr++) = *(from_ptr + 0); *(to_ptr++) = *(from_ptr + 3);
        }
    return to_buf;
    }

    // Initialize these values to shut the compiler up during -Wall.  We
    // don't bother checking the validity of to_format and from_format
    // because the python wrapper ensures they're valid.
    tr = tg = tb = ta = fr = fg = fb = fa = 0;

    for (i = 0; i < to_bpp; i ++) {
        if (to_format[i] == 'R') tr = i;
        else if (to_format[i] == 'G') tg = i;
        else if (to_format[i] == 'B') tb = i;
        else if (to_format[i] == 'A') ta = i;
    }
    for (i = 0; i < from_bpp; i ++) {
        if (from_format[i] == 'R') fr = i;
        else if (from_format[i] == 'G') fg = i;
        else if (from_format[i] == 'B') fb = i;
        else if (from_format[i] == 'A') fa = i;
    }

    LOOP_START {
        *(to_ptr + tr) = *(from_ptr + fr);
        *(to_ptr + tg) = *(from_ptr + fg);
        *(to_ptr + tb) = *(from_ptr + fb);
        if (to_bpp == 4)
            *(to_ptr + ta) = (from_bpp==4)?*(from_ptr + fa):255;

        to_ptr += to_bpp;
    }
    return to_buf;
}


unsigned char* get_raw_bytes(char *format, unsigned char *dstbuf)
{
    unsigned int w, h, bufsize;
    unsigned char *srcbuf;

    w = imlib_image_get_width(),
    h = imlib_image_get_height(),
    bufsize = get_raw_bytes_size(format);

    imlib_image_set_has_alpha(1);
    srcbuf = (unsigned char *)imlib_image_get_data_for_reading_only();
    if (dstbuf == 0)
        dstbuf = (unsigned char *)malloc(bufsize);

    if (!strcmp(format, "BGRA"))
        memcpy(dstbuf, srcbuf, bufsize);
    else
        dstbuf = convert_raw_rgba_bytes("BGRA", format, srcbuf, dstbuf, w, h);
    return dstbuf;
}
