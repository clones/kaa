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
#include <inttypes.h>

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


// "Pixel channel": dereferences ptr and takes the octet at byte position 'pos'
// (where pos 0 is the LSB)
#define PCH_0(ptr, pos) (*(ptr) & (255 << (8*pos)))
// Take a pixel channel and shift it "right" by some number of positions.
// It's actally a left bit shift, but because we label our formats from LSB -> MSB,
// moving a channel "right" moves it towards the MSB, which is actually a left shift.
#define PCH_R(ptr, pos, shift) (PCH_0(ptr, pos) << (8 * shift))
// Take a pixel channel and shift it "left" by some number of positions.
#define PCH_L(ptr, pos, shift) (PCH_0(ptr, pos) >> (8 * shift))

#define SWIZZLE_START(s_inc, d_inc) do { \
    uint32_t *s = (uint32_t *)from_buf, *d = (uint32_t *)to_buf; \
    for (; (unsigned char *)s < from_buf + w*h*from_bpp; s += s_inc, d += d_inc)
#define SWIZZLE_END } while(0)

// Used for swizzling 32-bit to 32-bit pixels (e.g. BGRA -> RGBA)
#define SWIZZLE(exp) \
    SWIZZLE_START(1, 1) { \
        *d = (exp); \
    } SWIZZLE_END

// Use for swizzling 32-bit to 24-bit pixels (e.g. BGRA -> RGB)
#define SWIZZLE43(exp1, exp2, exp3) \
    SWIZZLE_START(4, 3) { \
        *d = (exp1); \
        *(d+1) = (exp2); \
        *(d+2) = (exp3); \
    } SWIZZLE_END

// Used for swizzling 24-bit to 32-bit pixls (e.g. RGB -> BGRA)
#define SWIZZLE34(exp1, exp2, exp3, exp4) \
    SWIZZLE_START(3, 4) { \
        *d = (exp1); \
        *(d+1) = (exp2); \
        *(d+2) = (exp3); \
        *(d+3) = (exp4); \
    } SWIZZLE_END

unsigned char* convert_raw_rgba_bytes(char *from_format, char *to_format,
                                      unsigned char *from_buf, unsigned char *to_buf,
                                      int w, int h)
{
    int from_bpp, to_bpp, i;
    from_bpp = get_format_bpp(from_format);
    to_bpp = get_format_bpp(to_format);

    if (to_buf == 0)
        to_buf = (unsigned char *)malloc(w*h*to_bpp);

    /* Optimize for some common cases.  Note that the string formats indicate
     * the byte order of the buffer on little-endian machines, so B is the LSB
     * and A is the MSB.
     */ 
    if (!strcmp(from_format, "BGRA") && !strcmp(to_format, "RGB")) {
        // BGRA BGRA BGRA BGRA (4) -> RGBR GBRG BRGB (3)
        SWIZZLE43(/*R*/PCH_L(s, 2, 2)   | /*G*/PCH_0(s, 1)      | /*B*/PCH_R(s, 0, 2)   | /*R*/PCH_R(s+1, 2, 1),
                  /*G*/PCH_L(s+1, 1, 1) | /*B*/PCH_R(s+1, 0, 1) | /*R*/PCH_0(s+2, 2)    | /*G*/PCH_R(s+2, 1, 2),
                  /*B*/PCH_0(s+2, 0)    | /*R*/PCH_L(s+3, 2, 1) | /*G*/PCH_R(s+3, 1, 1) | /*B*/PCH_R(s+3, 0, 3));
    } 
    else if (!strcmp(from_format, "RGB") && !strcmp(to_format, "BGRA")) {
        // RGBR GBRG BRGB (3) -> BGRA BGRA BGRA BGRA (4)
        SWIZZLE34(/*B*/PCH_L(s, 2, 2)   | /*G*/PCH_0(s, 1)      | /*R*/PCH_R(s, 0, 2)   | /*A*/0xff000000,
                  /*B*/PCH_L(s+1, 1, 1) | /*G*/PCH_R(s+1, 0, 1) | /*R*/PCH_L(s, 3, 1)   | /*A*/0xff000000,
                  /*B*/PCH_0(s+2, 0)    | /*G*/PCH_L(s+1, 3, 2) | /*R*/PCH_0(s+1, 2)    | /*A*/0xff000000,
                  /*B*/PCH_L(s+2, 3, 3) | /*G*/PCH_L(s+2, 2, 1) | /*R*/PCH_R(s+2, 1, 1) | /*A*/0xff000000);
    } 
    else if ((!strcmp(from_format, "BGRA") && !strcmp(to_format, "RGBA")) ||
             (!strcmp(from_format, "RGBA") && !strcmp(to_format, "BGRA")))
        // BGRA -> RGBA
        SWIZZLE(/*R*/PCH_L(s, 2, 2) | /*G*/PCH_0(s, 1) | /*B*/PCH_R(s, 0, 2) | /*A*/PCH_0(s, 3));
    else {
        // Generic, anything-to-anything conversion code.  This is pretty slow.
        unsigned char fr, fb, fg, fa, tr, tb, tg, ta, *s, *d;

        if (to_buf == from_buf)
            // Caller requested in-place swizzle but the slow path can't
            // handle that, so allocate a new buffer.
            to_buf = (unsigned char *)malloc(w*h*to_bpp);

        tr = tg = tb = ta = fr = fg = fb = fa = 0;
        for (i = 0; i < to_bpp; i++) {
            if (to_format[i] == 'R') tr = i;
            else if (to_format[i] == 'G') tg = i;
            else if (to_format[i] == 'B') tb = i;
            else if (to_format[i] == 'A') ta = i;
        }
        for (i = 0; i < from_bpp; i++) {
            if (from_format[i] == 'R') fr = i;
            else if (from_format[i] == 'G') fg = i;
            else if (from_format[i] == 'B') fb = i;
            else if (from_format[i] == 'A') fa = i;
        }

        if (to_bpp == 4 && from_bpp == 4) {
            for (s=from_buf, d=to_buf; s < from_buf + w*h*from_bpp; s += from_bpp, d += to_bpp) {
                d[tr] = s[fr];
                d[tg] = s[fg];
                d[tb] = s[fb];
                d[ta] = s[fa];
            }
        } else {
            for (s=from_buf, d=to_buf; s < from_buf + w*h*from_bpp; s += from_bpp, d += to_bpp) {
                d[tr] = s[fr];
                d[tg] = s[fg];
                d[tb] = s[fb];
                if (to_bpp == 4)
                    d[ta] = (from_bpp == 4) ? s[fa] : 0xff;
            }
        }
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
