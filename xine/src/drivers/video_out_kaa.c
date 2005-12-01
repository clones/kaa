/*
 * ----------------------------------------------------------------------------
 * Video driver for kaa.xine - provides BGRA OSD and frame-to-buffer features
 * ----------------------------------------------------------------------------
 * $Id$
 *
 * ----------------------------------------------------------------------------
 * Copyright (C) 2004-2005 Jason Tackaberry <tack@sault.org>
 *
 * Maintainer:    Jason Tackaberry <tack@sault.org>
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


#include <math.h>
#include <malloc.h>
#include <assert.h>
#ifndef __USE_XOPEN2K
#define __USE_XOPEN2K // for pthread_mutex_timedlock
#endif
#include <pthread.h>

#include "../config.h"
#include "video_out_kaa.h"

// Uncomment this for profiling info.
//#define STOPWATCH 4

#define clamp(a,min,max) (((a)>(max))?(max):(((a)<(min))?(min):(a)))

static int _kaa_blend_osd(kaa_driver_t *this, kaa_frame_t *frame);


#ifdef STOPWATCH
static void stopwatch(int n, char *text, ...)
{
    va_list ap;
    struct timezone tz;
    static struct {
        struct timeval tv, last_tv;
        char text[250];
    } t[10];

    if (n > STOPWATCH)
        return;
    gettimeofday(&t[n].tv, &tz);
    if (!text) {
        fprintf(stderr, "@@@ Stopwatch (%d): %s: %ld usec\n", n, t[n].text,
               (t[n].tv.tv_sec - t[n].last_tv.tv_sec) * 1000000 +
               (t[n].tv.tv_usec - t[n].last_tv.tv_usec));
    } else {
        t[n].last_tv.tv_sec = t[n].tv.tv_sec;
        t[n].last_tv.tv_usec = t[n].tv.tv_usec;

        va_start(ap, text);
        vsprintf(t[n].text, text, ap);
        va_end(ap);
    }
}
#else
#define stopwatch(n, text, ...)
#endif


#if defined(ARCH_X86) || defined(ARCH_X86_64)
    #define YUY2_SIZE_THRESHOLD   400*280

    #define C64(x) ((uint64_t)((x)|(x)<<16))<<32 | (uint64_t)(x) | (uint64_t)(x)<<16
    static uint64_t  __attribute__((used)) __attribute__((aligned(8))) MM_global_alpha;
    static uint64_t  __attribute__((used)) __attribute__((aligned(8))) MM_ROUND = C64(0x80);
    #ifdef ARCH_X86_64
        #define REG_c  "rcx"
    #else
        #define REG_c  "ecx"
    #endif
#else
    #define YUY2_SIZE_THRESHOLD   2000*2000
#endif



/////////////////////////////////////////////////////////////////////////////


#define FP_BITS 18
#define rgb2y(R,G,B) ( (Y_R[ R ] + Y_G[ G ] + Y_B[ B ]) >> FP_BITS )
#define rgb2u(R,G,B) ( (U_R[ R ] + U_G[ G ] + U_B[ B ]) >> FP_BITS )
#define rgb2v(R,G,B) ( (V_R[ R ] + V_G[ G ] + V_B[ B ]) >> FP_BITS )

static int Y_R[256], Y_G[256], Y_B[256],
           U_R[256], U_G[256], U_B[256],
           V_R[256], V_G[256], V_B[256];

static void
init_rgb2yuv_tables()
{
    int i;
    #define myround(n) (n >= 0) ? (int)(n + 0.5) : (int)(n - 0.5);

    for (i = 0; i < 256; i++) {
        Y_R[i] = myround(0.299 * (double)i * 219.0 / 255.0 * (double)(1<<FP_BITS));
        Y_G[i] = myround(0.587 * (double)i * 219.0 / 255.0 * (double)(1<<FP_BITS));
        Y_B[i] = myround((0.114 * (double)i * 219.0 / 255.0 *
                  (double)(1<<FP_BITS)) + (double)(1<<(FP_BITS-1)) +
                  (16.0 * (double)(1<<FP_BITS)));
        U_R[i] = myround(-0.168736 * (double)i * 224.0 / 255.0 *
                 (double)(1<<FP_BITS));
        U_G[i] = myround(-0.331264 * (double)i * 224.0 / 255.0 *
                 (double)(1<<FP_BITS));
        U_B[i] = myround((0.500 * (double)i * 224.0 / 255.0 *
                  (double)(1<<FP_BITS)) + (double)(1<<(FP_BITS-1)) +
                 (128.0 * (double)(1<<FP_BITS)));
        V_R[i] = myround(0.500 * (double)i * 224.0 / 255.0 * (double)(1<<FP_BITS));
        V_G[i] = myround(-0.418688 * (double)i * 224.0 / 255.0 *
                 (double)(1<<FP_BITS));
        V_B[i] = myround((-0.081312 * (double)i * 224.0 / 255.0 *
                  (double)(1<<FP_BITS)) + (double)(1<<(FP_BITS-1)) +
                 (128.0 * (double)(1<<FP_BITS)));
    }

}


static void
free_overlay_data(kaa_driver_t *this)
{
    int i, p;
    uint8_t **planes[] = { 
        this->osd_planes, this->osd_pre_planes,
        this->osd_alpha_planes, this->osd_pre_alpha_planes, NULL
    };

    for (p = 0; planes[p] != NULL; p++) {
        for (i = 0; i < 3; i++) {
            // plane[1] == plane[2] for alpha planes, so only free one.
            if (planes[p][i] && (p < 2 || i < 2))
                free(planes[p][i]);
            planes[p][i] = NULL;
        }
    }
}

static void
alloc_overlay_data(kaa_driver_t *this, int format)
{
    int w = this->osd_w, h = this->osd_h;

    free_overlay_data(this);

    if (format == XINE_IMGFMT_YV12) {
        this->osd_planes[0] = (uint8_t *)memalign(16, w * h);
        this->osd_planes[1] = (uint8_t *)memalign(16, w * h / 4);
        this->osd_planes[2] = (uint8_t *)memalign(16, w * h / 4);

        this->osd_alpha_planes[0] = (uint8_t *)memalign(16, w * h);
        this->osd_alpha_planes[1] = (uint8_t *)memalign(16, w * h / 4);
        this->osd_alpha_planes[2] = this->osd_alpha_planes[1];

        this->osd_pre_planes[0] = (uint8_t *)memalign(16, w * h);
        this->osd_pre_planes[1] = (uint8_t *)memalign(16, w * h / 4);
        this->osd_pre_planes[2] = (uint8_t *)memalign(16, w * h / 4);
        
        this->osd_pre_alpha_planes[0] = (uint8_t *)memalign(16, w * h);
        this->osd_pre_alpha_planes[1] = (uint8_t *)memalign(16, w * h / 4);
        this->osd_pre_alpha_planes[2] = this->osd_pre_alpha_planes[1];

        this->osd_strides[0] = w;
        this->osd_strides[1] = this->osd_strides[2] = w >> 1;
    }
    else if (format == XINE_IMGFMT_YUY2) {
        this->osd_planes[0] = (uint8_t *)memalign(16, w * h * 2);
        this->osd_planes[1] = this->osd_planes[2] = 0;

        this->osd_alpha_planes[0] = (uint8_t *)memalign(16, w * h * 2);
        this->osd_alpha_planes[1] = this->osd_alpha_planes[2] = 0;

        this->osd_pre_planes[0] = (uint8_t *)memalign(16, w * h * 2);
        this->osd_pre_planes[1] = this->osd_pre_planes[2] = 0;

        this->osd_pre_alpha_planes[0] = (uint8_t *)memalign(16, w * h * 2);
        this->osd_pre_alpha_planes[1] = this->osd_pre_alpha_planes[2] = 0;

        this->osd_strides[0] = w * 2;
        this->osd_strides[1] = this->osd_strides[2] = 0;
    } else {
        printf("ERROR: unsupported frame format; osd disabled.\n");
    }

    this->osd_format = format;
}


static int
_check_bounds(kaa_driver_t *this, const char *func, int x, int y, int w, int h)
{
    if (x < 0 || y < 0 || w <= 0 || h <= 0 || 
        x >= this->osd_w || x+w > this->osd_w || 
        y >= this->osd_h || y+h > this->osd_h) {
        printf("! WARNING: rect (%d,%d %dx%d) passed to %s outside bounds (%dx%d)\n", 
           x, y, w, h, func, this->osd_w, this->osd_h);
        return 0;
    }
    return 1;
}

#define check_bounds(this, x, y, w, h) _check_bounds(this, __FUNCTION__, x, y, w, h)


static void
calculate_slice(kaa_driver_t *this)
{
    int x, y, n_plane, w, h, row_stride, slice_y1 = -2, slice_y2 = -2;
    uint8_t *p;

    n_plane = this->osd_format == XINE_IMGFMT_YV12 ? 1 : 0;
    p = this->osd_alpha_planes[n_plane];
    row_stride = this->osd_strides[n_plane];
    h = this->osd_h >> n_plane;
    w = row_stride & ~7; // round row stride down to nearest multiple of 8

    stopwatch(3, "calculate_slice: %dx%d", w, h);
    for (y = 0; y < h; y++) {
        for (x = 0; x < w; x += 8) {
            if (*(uint64_t *)(p + x)) {
                if (slice_y1 == -2)
                    slice_y1 = y;
                else
                    slice_y2 = y;
                break;
            }
        }
        p += row_stride;
    }
    stopwatch(3, NULL);
    this->osd_slice_y = clamp((slice_y1 - 2) * (n_plane + 1), 0, this->osd_h);
    this->osd_slice_h = clamp((slice_y2 + 2) * (n_plane + 1), 0, this->osd_h) - this->osd_slice_y;
}

static void
convert_bgra_to_yuy2a(kaa_driver_t *this, int rx, int ry, int rw, int rh)
{
    uint8_t r1, g1, b1, a1, r2, g2, b2, a2, *src_ptr, *dst_ptr, *dst_a_ptr;
    int x, y, dst_stride, src_stride;
 
    stopwatch(2, "convert_bgra_to_yuy2a (%d,%d %dx%d)", rx, ry, rw, rh);
    src_stride = this->osd_stride;
    dst_stride = this->osd_strides[0];
    src_ptr = this->osd_buffer + (rx*4) + (ry*src_stride);
    dst_ptr = this->osd_planes[0] + (rx*2 + ry * dst_stride);
    dst_a_ptr = this->osd_alpha_planes[0] + (rx*2 + ry * dst_stride);
    // This is not the most graceful code ...
    for (y = 0; y < rh; y++) {
        for (x = 0; x < rw; x+=2) {
            b1 = src_ptr[4*x+0];
            g1 = src_ptr[4*x+1];
            r1 = src_ptr[4*x+2];
            a1 = src_ptr[4*x+3];
            b2 = src_ptr[4*x+4];
            g2 = src_ptr[4*x+5];
            r2 = src_ptr[4*x+6];
            a2 = src_ptr[4*x+7];

            dst_ptr[2*x] = rgb2y(r1, g1, b1);
            dst_ptr[2*x+2] = rgb2y(r2, g2, b2);
            dst_a_ptr[2*x] = a1;
            dst_a_ptr[2*x+2] = a2;

            dst_ptr[x*2+1] = rgb2u((r1+r2)>>1, (g1+g2)>>1, (b1+b2)>>1);
            dst_ptr[x*2+3] = rgb2v((r1+r2)>>1, (g1+g2)>>1, (b1+b2)>>1);
            dst_a_ptr[x*2+1] = dst_a_ptr[x*2+3] = (a1+a2)>>1;
        }
        dst_ptr += dst_stride;
        dst_a_ptr += dst_stride;
        src_ptr += src_stride;
    }
    stopwatch(2, NULL);
}
    


static void
convert_bgra_to_yv12a(kaa_driver_t *this, int rx, int ry, int rw, int rh)
{
    int x, y;
    unsigned char *y_ptr, *u_ptr, *v_ptr, *a_ptr, *uva_ptr, *src_ptr,
                  r, g, b, a;
    int luma_offset = rx + ry * this->osd_w;
    unsigned int src_stride = this->osd_stride, 
                 chroma_stride = this->osd_w >> 1;
    int chroma_offset = (rx >> 1) + (ry >> 1) * chroma_stride;

    if (!this->osd_planes[0]) // Not allocated yet.
        return;
    if (!check_bounds(this, rx, ry, rw, rh))
        return;

    stopwatch(2, "convert_bgra_to_yv12a (%d,%d %dx%d)", rx, ry, rw, rh);

    src_ptr = this->osd_buffer + (rx*4) + (ry*this->osd_stride);
    y_ptr = this->osd_planes[0] + luma_offset;
    u_ptr = this->osd_planes[1] + chroma_offset;
    v_ptr = this->osd_planes[2] + chroma_offset;
    a_ptr = this->osd_alpha_planes[0] + luma_offset;
    uva_ptr = this->osd_alpha_planes[1] + chroma_offset;

    for (y = 0; y < rh; y += 2) {
        for (x = 0; x < rw >> 1; x++) {
            b = src_ptr[8*x+0];
            g = src_ptr[8*x+1];
            r = src_ptr[8*x+2];
            a = src_ptr[8*x+3];

            y_ptr[2*x] = rgb2y(r, g, b);
            a_ptr[2*x] = a;

            b = (b + src_ptr[8*x+0+src_stride])>>1;
            g = (g + src_ptr[8*x+1+src_stride])>>1;
            r = (r + src_ptr[8*x+2+src_stride])>>1;
            u_ptr[x] = rgb2u(r, g, b);
            v_ptr[x] = rgb2v(r, g, b);
            uva_ptr[x] = (a + src_ptr[8*x+3+src_stride])>>1;

            y_ptr[2*x+1] = rgb2y(src_ptr[8*x+6], src_ptr[8*x+5], src_ptr[8*x+4]);
            a_ptr[2*x+1] = src_ptr[8*x+7];
        }
        y_ptr += this->osd_w;
        a_ptr += this->osd_w;
        src_ptr += src_stride;

        for (x = 0; x < rw >> 1; x++) {
            y_ptr[2*x] = rgb2y(src_ptr[8*x+2], src_ptr[8*x+1], src_ptr[8*x+0]);
            a_ptr[2*x] = src_ptr[8*x+3];
            y_ptr[2*x+1] = rgb2y(src_ptr[8*x+6], src_ptr[8*x+5], src_ptr[8*x+4]);
            a_ptr[2*x+1] = src_ptr[8*x+7];
        }
        y_ptr += this->osd_w;
        a_ptr += this->osd_w;
        src_ptr += src_stride;

        u_ptr += chroma_stride;
        v_ptr += chroma_stride;
        uva_ptr += chroma_stride;
    }
    stopwatch(2, NULL);
}

static void
convert_bgra_to_frame_format(kaa_driver_t *this, int rx, int ry, int rw, int rh)
{
    if (this->osd_format == XINE_IMGFMT_YV12)
        convert_bgra_to_yv12a(this, rx, ry, rw, rh);
    else if (this->osd_format == XINE_IMGFMT_YUY2)
        convert_bgra_to_yuy2a(this, rx, ry, rw, rh);
    calculate_slice(this);
}
        
static inline uint8_t
multiply_alpha(uint8_t r, uint8_t a)
{
    int temp = (r * a) + 0x80;
    return ((temp + (temp >> 8)) >> 8);
}



/// Blends src on top of dst at the given alpha level.
#define blend_byte(dst, src, alpha) multiply_alpha(dst, alpha) + src;

static inline void
premultiply_alpha_byte(uint8_t byte, uint8_t alpha,
                       uint8_t *dst_byte, uint8_t *dst_alpha,
                       int global_alpha)
{
    uint8_t a = (global_alpha < 255) ? alpha * global_alpha >> 8 : alpha;
    *dst_byte = multiply_alpha(byte, a);
    *dst_alpha = 255-a;
}



/**
 * \brief Alpha-multiplies 8 consecutive bytes. C version.
 */
static inline void
premultiply_alpha_byte_8_C(uint8_t *byte, uint8_t *alpha,
                           uint8_t *dst_byte, uint8_t *dst_alpha,
                           int global_alpha)
{
    int i;
    for (i = 0; i < 8; i++)
        premultiply_alpha_byte(*(byte++), *(alpha++), dst_byte++, dst_alpha++, global_alpha);
}


#if defined(ARCH_X86) || defined(ARCH_X86_64)
/**
 * \brief Alpha-multiplies 8 consecutive bytes. MMX version.
 */
static inline void
premultiply_alpha_byte_8_MMX(uint8_t *byte, uint8_t *alpha,
                             uint8_t *dst_byte, uint8_t *dst_alpha,
                             int global_alpha)
{
    asm volatile(
        ".balign 16 \n\t"

        "movq (%3), %%mm5\n\t"        // %mm5 = alpha
        "cmp $255, %4\n\t"           // don't apply layer alpha if it's 100% opaque
        "je 42f\n\t"

        // Modify alpha from image with layer alpha
        "movq %%mm5, %%mm6\n\t"       // %mm6 = %mm5 = alpha
        "punpcklbw %%mm7, %%mm5\n\t"  // %mm5 = low dword of alpha
        "punpckhbw %%mm7, %%mm6\n\t"  // %mm6 = hi dword of alpha
        "pmullw "MANGLE(MM_global_alpha)", %%mm5\n\t"  // alpha * global_alpha
        "pmullw "MANGLE(MM_global_alpha)", %%mm6\n\t"
        "psrlw $8, %%mm5\n\t"         // Divide by 256
        "psrlw $8, %%mm6\n\t"
        "packuswb %%mm6, %%mm5\n\t"   // Pack back into %mm5

        "42: \n\t"
        "movq %%mm4, %%mm6\n\t"       // %mm4 = %mm6 = 255
        "psubb %%mm5, %%mm6\n\t"      // %mm6 = 255 - alpha
        "movq %%mm6, (%1)\n\t"        // save modified alpha

        // Do alpha * bytes
        "movq (%2), %%mm0\n\t"        // %mm0 = byte
        "movq %%mm0, %%mm1\n\t"       // %mm1 = byte
        "punpcklbw %%mm7, %%mm0\n\t"  // %mm0 = low dword of bytes
        "punpckhbw %%mm7, %%mm1\n\t"  // %mm1 = hi dword of bytes
        "movq %%mm5, %%mm6\n\t"       // %mm5 = %mm6 = alpha
        "punpcklbw %%mm7, %%mm5\n\t"  // %mm5 = low dword alpha
        "punpckhbw %%mm7, %%mm6\n\t"  // %mm6 = hi dword alpha
        "pmullw %%mm5, %%mm0\n\t"     // alpha * bytes = (r*a)
        "pmullw %%mm6, %%mm1\n\t"
        // approximate division by 255
        "movq "MANGLE(MM_ROUND)", %%mm6\n\t"   // %mm4 = round
        "paddw %%mm6, %%mm0\n\t"      // (r*a) + 0x80
        "paddw %%mm6, %%mm1\n\t"
        "movq %%mm0, %%mm2\n\t"       // temp = (r*a) + 0x80
        "movq %%mm1, %%mm3\n\t"
        "psrlw $8, %%mm0\n\t"         // temp >> 8
        "psrlw $8, %%mm1\n\t"
        "paddw %%mm2, %%mm0\n\t"      // temp + (temp >> 8)
        "paddw %%mm3, %%mm1\n\t"
        "psrlw $8, %%mm0\n\t"         // (temp+(temp>>8))>>8
        "psrlw $8, %%mm1\n\t"

        "packuswb %%mm1, %%mm0\n\t"
        "movq %%mm0, (%0)\n\t"
    :  "+r" (dst_byte),             // %0
       "+r" (dst_alpha)             // %1
    :  "r" (byte),                  // %2
       "r" (alpha),                 // %3
       "r" (global_alpha));         // %4
}
#endif


static void
(*premultiply_alpha_byte_8)(uint8_t *byte, uint8_t *alpha,
                            uint8_t *dst_byte, uint8_t *dst_alpha,
                            int global_alpha);

static void
image_premultiply_alpha(kaa_driver_t *this, int rx, int ry, int rw, int rh)
{
    uint8_t *ptr[3], *alpha_ptr[3], *pre_ptr[3], *pre_alpha_ptr[3];
    int i, x, y, n_planes, offset[3], global_alpha = this->osd_alpha;

    if (!this->osd_planes[0]) // Not allocated yet.
        return;

    if (!check_bounds(this, rx, ry, rw, rh))
        return;

    stopwatch(2, "premultiply_alpha (%d,%d %dx%d)", rx, ry, rw, rh);

    if (global_alpha > 255)
        global_alpha = 255;

    if (this->osd_format == XINE_IMGFMT_YV12) {
        offset[0] = rx + ry * this->osd_strides[0];
        offset[1] = offset[2] = (rx >> 1) + (ry >> 1) * this->osd_strides[1];
    } else {
        offset[0] = (rx*2) + ry * this->osd_strides[0];
        offset[1] = offset[2] = 0;
        rw *= 2;
    }

    for (i = 0; i < 3 && this->osd_planes[i]; i++) {
        ptr[i] = this->osd_planes[i] + offset[i];
        alpha_ptr[i] = this->osd_alpha_planes[i] + offset[i];
        pre_ptr[i] = this->osd_pre_planes[i] + offset[i];
        pre_alpha_ptr[i] = this->osd_pre_alpha_planes[i] + offset[i];
    }

#if defined(ARCH_X86) || defined(ARCH_X86_64)
    if (xine_mm_accel() & MM_ACCEL_X86_MMX) {
        MM_global_alpha = C64(global_alpha);
        asm volatile(
            "pxor %%mm7, %%mm7\n\t"                // zero out %mm7
            "pcmpeqb %%mm4, %%mm4\n\t"             // %mm4 = 255's
            ::: "memory"
        );
    }
#endif

    for (y = 0; y < rh; y++) {
        n_planes = 1;
        for (x = 0; x < rw; x += 8)
            premultiply_alpha_byte_8(&ptr[0][x], &alpha_ptr[0][x], &pre_ptr[0][x], &pre_alpha_ptr[0][x], global_alpha);

        for (; x < rw; x++)
            premultiply_alpha_byte(ptr[0][x], alpha_ptr[0][x], &pre_ptr[0][x], &pre_alpha_ptr[0][x], global_alpha);

        if (y % 2 == 0 && this->osd_format == XINE_IMGFMT_YV12) {
            for (x = 0; x < (rw >> 1); x += 8) {
                premultiply_alpha_byte_8(&ptr[1][x], &alpha_ptr[1][x], &pre_ptr[1][x], &pre_alpha_ptr[1][x], global_alpha);
                premultiply_alpha_byte_8(&ptr[2][x], &alpha_ptr[2][x], &pre_ptr[2][x], &pre_alpha_ptr[2][x], global_alpha);
            }
            for (; x < rw >> 1; x++) {
                premultiply_alpha_byte(ptr[1][x], alpha_ptr[1][x], &pre_ptr[1][x], &pre_alpha_ptr[1][x], global_alpha);
                premultiply_alpha_byte(ptr[2][x], alpha_ptr[2][x], &pre_ptr[2][x], &pre_alpha_ptr[2][x], global_alpha);
            }
            n_planes = 3;
        }

        for (i = 0; i < n_planes; i++) {
            ptr[i] += this->osd_strides[i];
            alpha_ptr[i] += this->osd_strides[i];
            pre_ptr[i] += this->osd_strides[i];
            pre_alpha_ptr[i] += this->osd_strides[i];
        }
    }
#if defined(ARCH_X86) || defined(ARCH_X86_64)
    if (xine_mm_accel() & MM_ACCEL_X86_MMX)
        asm volatile( "emms\n\t" ::: "memory" );
#endif
    stopwatch(2, NULL);
}

static inline void
blend_plane_C(int w, int slice_h, uint8_t *dst, uint8_t *src,
              uint8_t *overlay, uint8_t *alpha, int frame_stride,
              int overlay_stride)
{
    int x, y;
    for (y = 0; y < slice_h; y++) {
        for (x = 0; x < w; x++)
            *(dst + x) = blend_byte(*(src+x), *(overlay+x), *(alpha+x));
        dst += frame_stride;
        src += frame_stride;
        overlay += overlay_stride;
        alpha += overlay_stride;
    }
}


#if defined(ARCH_X86) || defined(ARCH_X86_64)
static inline void
blend_plane_MMX(int w, int slice_h, uint8_t *dst, uint8_t *src,
                uint8_t *overlay, uint8_t *alpha, int frame_stride,
                int overlay_stride)
{
    int y, q = w / 8, r = w % 8;

    assert(w <= frame_stride && w <= overlay_stride);

    for (y = 0; y < slice_h; y++) {
        if (q) {
            asm volatile(
                ".balign 16 \n\t"
                "xor %%"REG_c", %%"REG_c"\n\t"

                "1: \n\t"
                "movq (%1, %%"REG_c"), %%mm0\n\t"        // %mm0 = mpi
                "movq %%mm0, %%mm1\n\t"       // %mm1 = mpi
                "movq (%3, %%"REG_c"), %%mm2\n\t"        // %mm2 = %mm3 = 255 - alpha
                "movq %%mm2, %%mm3\n\t"

                "punpcklbw %%mm7, %%mm0\n\t"  // %mm0 = low dword of mpi
                "punpckhbw %%mm7, %%mm1\n\t"  // %mm1 = hi dword of mpi
                "punpcklbw %%mm7, %%mm2\n\t"  // %mm0 = low dword of 255-a
                "punpckhbw %%mm7, %%mm3\n\t"  // %mm1 = hi dword of 255-a
                "pmullw %%mm2, %%mm0\n\t"     // (255-a) * mpi = (r*a)
                "pmullw %%mm3, %%mm1\n\t"
                // approximate division by 255
                "paddw %%mm5, %%mm0\n\t"      // (r*a) + 0x80
                "paddw %%mm5, %%mm1\n\t"
                "movq %%mm0, %%mm2\n\t"       // temp = (r*a) + 0x80
                "movq %%mm1, %%mm3\n\t"
                "psrlw $8, %%mm0\n\t"         // temp >> 8
                "psrlw $8, %%mm1\n\t"
                "paddw %%mm2, %%mm0\n\t"      // temp + (temp >> 8)
                "paddw %%mm3, %%mm1\n\t"
                "psrlw $8, %%mm0\n\t"         // (temp+(temp>>8))>>8
                "psrlw $8, %%mm1\n\t"
                // MPI plane now alpha-multiplied. Add to premultiplied
                // overlay plane.
                "movq (%2, %%"REG_c"), %%mm2\n\t"        // %mm2 = src image (overlay)
                "packuswb %%mm1, %%mm0\n\t"
                "paddb %%mm2, %%mm0\n\t"
                "movq %%mm0, (%0, %%"REG_c")\n\t"        // Store to dst (mpi)

                "add $8, %%"REG_c"\n\t"
                "cmp %4, %%"REG_c"\n\t"
                "jb 1b \n\t"
            : "+r" (dst),
              "+r" (src),
              "+r" (overlay),
              "+r" (alpha)
            : "m" (w)
            : "%"REG_c);
        }
        // Blend the last few pixels of this row ...
        if (r) {
            uint8_t *end = dst + r;
            for (; dst < end; dst++, src++, alpha++, overlay++)
                *dst = blend_byte(*src, *overlay, *alpha);
        }
        src += frame_stride;
        dst += frame_stride;
        alpha += overlay_stride;
        overlay += overlay_stride;
    }
}
#endif

static void
(*blend_plane)(int w, int slice_h, uint8_t *dst, uint8_t *src,
               uint8_t *overlay, uint8_t *alpha, int frame_stride,
               int overlay_stride);


static inline void
blend_image(kaa_driver_t *this, vo_frame_t *frame)
{
    int slice_y, slice_h, w, i, c, plane;
    uint8_t *dst_frame_planes[3], *src_frame_planes[3], *overlay, *src, *dst, *alpha,
            *overlay_planes[3], *alpha_planes[3];

    if (!this->osd_planes[0]) // Not allocated yet.
        return;

    // Clip the slice to the frame image.
    slice_y = clamp(this->osd_slice_y, 0, frame->height);
    slice_h = clamp(this->osd_slice_h, 0, frame->height - slice_y);

    stopwatch(5, "blend_image (0,%d, %dx%d)",  slice_y, this->osd_w, slice_h);

    for (i = 0, c = 0; i < 3; i++, c = 1)  {
        // Setup buffer positions for overlay, mpi src and mpi dst.
        overlay_planes[i] = this->osd_pre_planes[i];
        alpha_planes[i] = this->osd_pre_alpha_planes[i];
        dst_frame_planes[i] = frame->base[i] + ((slice_y >> c) * frame->pitches[i]);
        src_frame_planes[i] = frame->base[i] + ((slice_y >> c) * frame->pitches[i]);
        overlay_planes[i] += (slice_y >> c) * this->osd_strides[i];
        alpha_planes[i] += (slice_y >> c) * this->osd_strides[i];
    }

#if defined(ARCH_X86) || defined(ARCH_X86_64)
    if (xine_mm_accel() & MM_ACCEL_X86_MMX) {
        asm volatile(
            "pxor %%mm7, %%mm7\n\t"                // zero out %mm7
            "movq "MANGLE(MM_ROUND)", %%mm5\n\t"   // %mm5 = round
            ::: "memory"
        );
    }
#endif

    w = this->osd_w;
    if (frame->format == XINE_IMGFMT_YUY2)
        w *= 2;

    for (plane = 0; plane < 3 && this->osd_planes[plane]; plane++) {
        if (plane == 1 && frame->format == XINE_IMGFMT_YV12) {
            w >>= 1;
            slice_h >>= 1;
        }
        overlay = overlay_planes[plane];
        alpha = alpha_planes[plane];
        src = src_frame_planes[plane];
        dst = dst_frame_planes[plane];

        // Global alpha is 256 which means ignore per-pixel alpha. Do
        // straight memcpy.
        if (this->osd_alpha == 256) {
            xine_fast_memcpy(dst, overlay, this->osd_strides[plane] * slice_h);
        } else {
            blend_plane(w, slice_h, dst, src, overlay, alpha,
                        frame->pitches[plane], this->osd_strides[plane]);
        }
    }
#if defined(ARCH_X86) || defined(ARCH_X86_64)
    if (xine_mm_accel() & MM_ACCEL_X86_MMX)
        asm volatile( "emms\n\t" ::: "memory" );
#endif
    stopwatch(5, NULL);
}



/////////////////////////////////////////////////////////////////////////////



int
pthread_mutex_lock_timeout(pthread_mutex_t *lock, double timeout)
{
    struct timespec abstime;
    abstime.tv_sec = (int)floor(timeout);
    abstime.tv_nsec = (timeout-(double)abstime.tv_sec)*1000000000;
    return pthread_mutex_timedlock(lock, &abstime);
}


static void
_alloc_yv12(int width, int height, unsigned char **base, 
            unsigned char *planes[3], int strides[3])
{
    int y_size, uv_size;

    strides[0] = 8*((width + 7) / 8);
    strides[1] = 8*((width + 15) / 16);
    strides[2] = 8*((width + 15) / 16);
    
    y_size  = strides[0] * height;
    uv_size = strides[1] * ((height+1)/2);
 
    if (*base)
        free(*base);
           
    *base = (unsigned char *)xine_xmalloc(y_size + 2*uv_size);
    
    planes[0] = *base;
    planes[1] = *base + y_size + uv_size;
    planes[2] = *base + y_size;
}



static uint32_t 
kaa_get_capabilities(vo_driver_t *this_gen)
{
    //kaa_driver_t *this = (kaa_driver_t *)this_gen;
    //printf("kaa: get_capabilities\n");
    return VO_CAP_YV12 | VO_CAP_YUY2;
    //return this->passthrough->get_capabilities(this->passthrough);
}

static void
kaa_frame_field(vo_frame_t *frame_gen, int which)
{
    kaa_frame_t *frame = (kaa_frame_t *)frame_gen;
    //printf("kaa_frame_field %d\n", which);
    frame->passthrough_frame->field(frame->passthrough_frame, which);
}

static void
kaa_frame_proc_frame(vo_frame_t *frame_gen)
{
    kaa_frame_t *frame = (kaa_frame_t *)frame_gen;
    //printf("kaa_frame_proc_frame\n");
    frame->passthrough_frame->proc_frame(frame->passthrough_frame);
}

static void
kaa_frame_dispose(vo_frame_t *vo_img)
{
    kaa_frame_t *frame = (kaa_frame_t *)vo_img;
    //printf("kaa_frame_dispose\n");
    pthread_mutex_destroy(&frame->vo_frame.mutex);
    pthread_mutex_destroy(&frame->bgra_lock);
    if (frame->yv12_buffer)
        free(frame->yv12_buffer);
    if (frame->bgra_buffer)
        free(frame->bgra_buffer);

    // Why does this segfault?
    //if (frame->passthrough_frame)
    //    frame->passthrough_frame->dispose(frame->passthrough_frame);
    frame->yuv2rgb->dispose (frame->yuv2rgb);
    free(frame);
}

void vo_frame_inc_lock(vo_frame_t *img)
{
}

void vo_frame_dec_lock(vo_frame_t *img)
{
}


static vo_frame_t *
kaa_alloc_frame(vo_driver_t *this_gen)
{
    kaa_frame_t *frame;
    kaa_driver_t *this = (kaa_driver_t *)this_gen;
    
    //printf("kaa_alloc_frame\n");
    frame = (kaa_frame_t *)xine_xmalloc(sizeof(kaa_frame_t));
    if (!frame)
        return NULL;

    pthread_mutex_init(&frame->vo_frame.mutex, NULL);
    pthread_mutex_init(&frame->bgra_lock, NULL);

    frame->yv12_buffer = frame->bgra_buffer = NULL;

    frame->vo_frame.base[0] = NULL;
    frame->vo_frame.base[1] = NULL;
    frame->vo_frame.base[2] = NULL;


    frame->passthrough_frame = this->passthrough->alloc_frame(this->passthrough);
    frame->passthrough_frame->free = vo_frame_dec_lock;
    frame->passthrough_frame->lock = vo_frame_inc_lock;

    if (frame->passthrough_frame->proc_frame)
        frame->vo_frame.proc_frame = kaa_frame_proc_frame;
    frame->vo_frame.field = kaa_frame_field;
    frame->vo_frame.dispose = kaa_frame_dispose;
    frame->vo_frame.driver = this_gen;

    frame->yuv2rgb = this->yuv2rgb_factory->create_converter(this->yuv2rgb_factory);
    frame->driver = this;
    return (vo_frame_t *)frame;
}

static void 
kaa_update_frame_format (vo_driver_t *this_gen,
                vo_frame_t *frame_gen,
                uint32_t width, uint32_t height,
                double ratio, int format, int flags) 
{
    kaa_driver_t *this = (kaa_driver_t *)this_gen;
    kaa_frame_t *frame = (kaa_frame_t *)frame_gen;

    //printf("kaa_update_frame_format: %x format=%d  %dx%d\n", frame, format, width, height);

    // XXX: locking in this function risks deadlock.

    frame_gen->proc_called=0;
    this->passthrough->update_frame_format(this->passthrough,
        frame->passthrough_frame, width, height, ratio, format, flags);

    xine_fast_memcpy(&frame->vo_frame.pitches, frame->passthrough_frame->pitches, sizeof(int)*3);
    xine_fast_memcpy(&frame->vo_frame.base, frame->passthrough_frame->base, sizeof(char *)*3);

/*
    // Allocate memory for the desired frame format and size
    if (frame->width != width || frame->height != height || format != frame->format) {
        // Free memory from old frame configuration
        if (frame->vo_frame.base[0])
            free(frame->vo_frame.base[0]);
        if (frame->vo_frame.base[1]) {
            free(frame->vo_frame.base[1]);
            free(frame->vo_frame.base[2]);
        }

        frame->vo_frame.pitches[0] = frame->passthrough_frame->pitches[0];
        frame->vo_frame.pitches[1] = frame->passthrough_frame->pitches[1];
        frame->vo_frame.pitches[2] = frame->passthrough_frame->pitches[2];

        if (format == XINE_IMGFMT_YV12) {
            // Align pitch to 16 byte multiple.
            frame->vo_frame.base[0] = (uint8_t *)memalign(16, frame->vo_frame.pitches[0] * height);
            frame->vo_frame.base[1] = (uint8_t *)memalign(16, frame->vo_frame.pitches[1] * height);
            frame->vo_frame.base[2] = (uint8_t *)memalign(16, frame->vo_frame.pitches[2] * height);
        } else if (format == XINE_IMGFMT_YUY2) {
            frame->vo_frame.base[0] = (uint8_t *)memalign(16, frame->vo_frame.pitches[0] * height);
            frame->vo_frame.base[1] = NULL;
            frame->vo_frame.base[2] = NULL;
        }
    }
*/

    frame->width = width;
    frame->height = height;
    frame->format = format;
    frame->ratio = ratio;
    frame->flags = flags;
}

static int
kaa_redraw_needed(vo_driver_t *vo)
{
    kaa_driver_t *this = (kaa_driver_t *)vo;
    int redraw = this->needs_redraw;
    this->needs_redraw = 0;
    return redraw || this->passthrough->redraw_needed(this->passthrough);
}

static int
_kaa_frame_to_buffer(kaa_driver_t *this, kaa_frame_t *frame)
{
    int dst_width = this->send_frame_width == -1 ? frame->width : this->send_frame_width, 
        dst_height = this->send_frame_height == -1 ? frame->height : this->send_frame_height;
        dst_height = this->send_frame_height;

    if (dst_width == -1)
        dst_width = frame->width;
    if (dst_height == -1)
        dst_height = frame->height;

    if (pthread_mutex_lock_timeout(&frame->bgra_lock, 0.2) != 0) {
        printf("FAILED to acquire lock\n");
        return 0;
    }
    if (!frame->bgra_buffer || 
         frame->width != frame->yuv2rgb->source_width || 
         frame->height != frame->yuv2rgb->source_height ||
         frame->vo_frame.pitches[0] != frame->yuv2rgb->y_stride ||
         frame->vo_frame.pitches[1] != frame->yuv2rgb->uv_stride ||
         frame->yuv2rgb->dest_width != dst_width ||
         frame->yuv2rgb->dest_height != dst_height) {

        int y_stride = frame->vo_frame.pitches[0],
            uv_stride = frame->vo_frame.pitches[1];
        if (frame->bgra_buffer)
            free(frame->bgra_buffer);
        frame->bgra_buffer = malloc(frame->width*frame->height*4);

        if (frame->format == XINE_IMGFMT_YUY2 && dst_width*dst_height > YUY2_SIZE_THRESHOLD) {
            _alloc_yv12(frame->width, frame->height, &frame->yv12_buffer,
                        frame->yv12_planes, frame->yv12_strides);
            y_stride = frame->yv12_strides[0];
            uv_stride = frame->yv12_strides[1];
        }

        frame->yuv2rgb->configure(frame->yuv2rgb, frame->width, frame->height,
                                  y_stride, uv_stride,
                                  dst_width, dst_height, 4*(dst_width));
    }
    if (frame->format == XINE_IMGFMT_YV12) {
        stopwatch(0, "yv12 to bgra32");
        frame->yuv2rgb->yuv2rgb_fun (frame->yuv2rgb, frame->bgra_buffer,
                                     frame->vo_frame.base[0],  
                                     frame->vo_frame.base[1],  
                                     frame->vo_frame.base[2]);
        stopwatch(0, NULL);
    } else {
        stopwatch(0, "yuy2 to bgra32");
        if (dst_width*dst_height > YUY2_SIZE_THRESHOLD) {
            // Naive optimization: yuv2rgb has an accelerated version
            // but yuy22rgb doesn't.  So when the area of the image is
            // greater than the size threshold (determined empirically)
            // first convert the yuy2 image to yv12 and then convert
            // yv12 to rgb, both operations of which are accelerated.
            yuy2_to_yv12(frame->vo_frame.base[0], frame->vo_frame.pitches[0],
                         frame->yv12_planes[0], frame->yv12_strides[0],
                         frame->yv12_planes[1], frame->yv12_strides[1],
                         frame->yv12_planes[2], frame->yv12_strides[2],
                         frame->width, frame->height);
            frame->yuv2rgb->yuv2rgb_fun (frame->yuv2rgb, frame->bgra_buffer,
                                         frame->yv12_planes[0],
                                         frame->yv12_planes[1],
                                         frame->yv12_planes[2]);
        } else {
            frame->yuv2rgb->yuy22rgb_fun (frame->yuv2rgb, frame->bgra_buffer,
                                          frame->vo_frame.base[0]);
        }
        stopwatch(0, NULL);
    }
    this->send_frame_cb(dst_width, dst_height, frame->ratio, frame->bgra_buffer, &frame->bgra_lock,
                        this->send_frame_cb_data);
    return 1;
}

static int
_kaa_blend_osd(kaa_driver_t *this, kaa_frame_t *frame)
{
    pthread_mutex_lock(&this->osd_buffer_lock);
    int resized = frame->width != this->osd_w || frame->height != this->osd_h;
    if (resized || frame->format != this->osd_format) {
        this->osd_w = frame->width;
        this->osd_h = frame->height;
        this->osd_slice_h = frame->height;
        alloc_overlay_data(this, frame->format);
        if (this->osd_configure_cb && resized) {
            // XXX: could configure cb cause reentry here?  If so, will deadlock.
            this->osd_configure_cb(frame->width, frame->height, frame->ratio, this->osd_configure_cb_data);
        }
        convert_bgra_to_frame_format(this, 0, 0, frame->width, frame->height);
        image_premultiply_alpha(this, 0, 0, frame->width, frame->height);
    }
    if (this->osd_visible && this->osd_alpha > 0) 
        blend_image(this, &frame->vo_frame);
    pthread_mutex_unlock(&this->osd_buffer_lock);

    return 1;
}

static void 
kaa_display_frame (vo_driver_t *this_gen, vo_frame_t *frame_gen) 
{
    kaa_driver_t *this = (kaa_driver_t *)this_gen;
    kaa_frame_t *frame = (kaa_frame_t *)frame_gen;

    //printf("kaa_display_frame: %x draw=%x w=%d h=%d ratio=%.3f format=%d (yv12=%d yuy=%d)\n", frame, frame_gen->draw, frame->vo_frame.width, frame->height, frame->ratio, frame->format, XINE_IMGFMT_YV12, XINE_IMGFMT_YUY2);


    /*
    memcpy(frame->passthrough_frame->base[0], frame_gen->base[0], frame_gen->pitches[0] * frame->height);
    memcpy(frame->passthrough_frame->base[1], frame_gen->base[1], frame_gen->pitches[1] * (frame->height>>1));
    memcpy(frame->passthrough_frame->base[2], frame_gen->base[2], frame_gen->pitches[2] * (frame->height>>1));
    */

    this->cur_frame = frame;

    if (this->do_send_frame && this->send_frame_cb)
        _kaa_frame_to_buffer(this, frame);

    if (this->osd_buffer)
        _kaa_blend_osd(this, frame);

    if (frame->passthrough_frame->proc_slice) {
        // Serious kludge!  For passthrough drivers that do slices, we delay
        // processing them until now so that we have a chance to blend the 
        // OSD.
        int i;
        uint8_t *src[3] = {frame->vo_frame.base[0], frame->vo_frame.base[1], frame->vo_frame.base[2]};
        for (i = 0; i < frame->height / 16; i++) {
            frame->passthrough_frame->proc_slice(frame->passthrough_frame, src);
            src[0] += frame->vo_frame.pitches[0] * 16;
            src[1] += frame->vo_frame.pitches[1] * 8;
            src[2] += frame->vo_frame.pitches[2] * 8;
        }
    }


    if (this->passthrough && this->do_passthrough) 
        this->passthrough->display_frame(this->passthrough, frame->passthrough_frame);

    frame->vo_frame.free(&frame->vo_frame);

    pthread_mutex_unlock(&this->lock);

}

static int 
kaa_get_property (vo_driver_t *this_gen, int property) 
{
    kaa_driver_t *this = (kaa_driver_t *)this_gen;
    return this->passthrough->get_property(this->passthrough, property);
}

static int 
kaa_set_property (vo_driver_t *this_gen,
                int property, int value) 
{
    kaa_driver_t *this = (kaa_driver_t *)this_gen;
    /*
    printf("kaa_set_property %d=%d\n", property, value);
    switch(property) {
        case XINE_PARAM_VO_CROP_LEFT:
            this->crop_left = value;
            return value;

        case XINE_PARAM_VO_CROP_TOP:
            this->crop_top = value;
            return value;

        case XINE_PARAM_VO_CROP_RIGHT:
        case XINE_PARAM_VO_CROP_BOTTOM:
            return value;
    }
    */
    return this->passthrough->set_property(this->passthrough, property, value);
}

static void 
kaa_get_property_min_max (vo_driver_t *this_gen,
                     int property, int *min, int *max) 
{
    kaa_driver_t *this = (kaa_driver_t *)this_gen;
    //printf("kaa_get_property_min_max\n");
    this->passthrough->get_property_min_max(this->passthrough, property, min, max);
}

static int
kaa_gui_data_exchange (vo_driver_t *this_gen,
                 int data_type, void *data) 
{
    kaa_driver_t *this = (kaa_driver_t *)this_gen;

    switch(data_type) {
        case GUI_SEND_KAA_VO_SET_SEND_FRAME:
            this->do_send_frame = (int)data;
            break;

        case GUI_SEND_KAA_VO_SET_PASSTHROUGH:
            this->do_passthrough = (int)data;
            break;

        case GUI_SEND_KAA_VO_OSD_SET_VISIBILITY:
            this->osd_visible = (int)data;
            this->needs_redraw = 1;
            break;

        case GUI_SEND_KAA_VO_SET_SEND_FRAME_SIZE:
        {
            struct { int w, h; } *size = data;
            this->send_frame_width = size->w;
            this->send_frame_height = size->h;
            break;
        }
        case GUI_SEND_KAA_VO_OSD_INVALIDATE_RECT:
        {
            struct { int x, y, w, h; } *size = data;
            pthread_mutex_lock(&this->osd_buffer_lock);
            convert_bgra_to_frame_format(this, size->x, size->y, size->w, size->h);
            image_premultiply_alpha(this, size->x, size->y, size->w, size->h);
            pthread_mutex_unlock(&this->osd_buffer_lock);
            this->needs_redraw = 1;
            break;
        }
        case GUI_SEND_KAA_VO_OSD_SET_ALPHA:
        {
            int alpha = (int)data;
            pthread_mutex_lock(&this->osd_buffer_lock);
            if (alpha != this->osd_alpha) {
                this->osd_alpha = alpha;
                image_premultiply_alpha(this, 0, 0, this->osd_w, this->osd_h);
                this->needs_redraw = 1;
            }
            pthread_mutex_unlock(&this->osd_buffer_lock);
            break;
        }
        /*
        case GUI_SEND_KAA_VO_OSD_SET_SLICE:
        {
            struct { int y, h; } *slice = data;
            this->osd_slice_y = slice->y;
            this->osd_slice_h = slice->h;
            this->needs_redraw = 1;
            break;
        }
        */
    }
    return this->passthrough->gui_data_exchange(this->passthrough, data_type, data);
}

static void kaa_overlay_begin (vo_driver_t *this_gen,
                  vo_frame_t *frame_gen, int changed) {
  kaa_driver_t  *this  = (kaa_driver_t *) this_gen;

  this->alphablend_extra_data.offset_x = frame_gen->overlay_offset_x;
  this->alphablend_extra_data.offset_y = frame_gen->overlay_offset_y;
}


static void
kaa_overlay_blend(vo_driver_t *this_gen, vo_frame_t *frame_gen, vo_overlay_t *vo_overlay)
{
    kaa_frame_t *frame = (kaa_frame_t *)frame_gen;
    kaa_driver_t *this = (kaa_driver_t *)this_gen;

    //printf("kaa_overlay_blend: format=%d overlay=%p crop_left=%d\n", frame->format, vo_overlay, frame_gen->crop_left);
    if (frame->format == XINE_IMGFMT_YV12)
       _x_blend_yuv(frame->vo_frame.base, vo_overlay,
                      frame->width, frame->height,
                      frame->vo_frame.pitches, &this->alphablend_extra_data);
    else
       _x_blend_yuy2(frame->vo_frame.base[0], vo_overlay,
                      frame->width, frame->height,
                      frame->vo_frame.pitches[0], &this->alphablend_extra_data);
}

static void
kaa_dispose(vo_driver_t *this_gen)
{
    kaa_driver_t *this = (kaa_driver_t *)this_gen;

    //printf("kaa_dispose\n");
    this->yuv2rgb_factory->dispose(this->yuv2rgb_factory);
    free_overlay_data(this);
    pthread_mutex_destroy(&this->lock);
    pthread_mutex_destroy(&this->osd_buffer_lock);
    free(this);
}

static vo_driver_t *
kaa_open_plugin(video_driver_class_t *class_gen, const void *visual_gen)
{
    kaa_class_t *class = (kaa_class_t *)class_gen;
    kaa_visual_t *visual = (kaa_visual_t *)visual_gen;
    kaa_driver_t *this;

    // This deadlocks -- xine-lib needs fixing.  For now, caller will have to do this.
    /*
    vo_driver_t *passthrough;
    passthrough = _x_load_video_output_plugin(class->xine, visual->passthrough_driver,
                                              visual->passthrough_visual_type, visual->passthrough_visual);
    if (!passthrough) {
        return NULL;
    }
    */
    //printf("kaa_open_plugin\n");
    this = (kaa_driver_t *)xine_xmalloc(sizeof(kaa_driver_t));
    memset(this, 0, sizeof(kaa_driver_t));
    if (!this)
        return NULL;

    this->xine = class->xine;
    this->config = class->config;
    pthread_mutex_init(&this->lock, NULL);
    pthread_mutex_init(&this->osd_buffer_lock, NULL);
    
    this->vo_driver.get_capabilities        = kaa_get_capabilities;
    this->vo_driver.alloc_frame             = kaa_alloc_frame;
    this->vo_driver.update_frame_format     = kaa_update_frame_format;
    this->vo_driver.overlay_begin           = kaa_overlay_begin;
    this->vo_driver.overlay_blend           = kaa_overlay_blend;
    this->vo_driver.overlay_end             = NULL;
    this->vo_driver.display_frame           = kaa_display_frame;
    this->vo_driver.get_property            = kaa_get_property;
    this->vo_driver.set_property            = kaa_set_property;
    this->vo_driver.get_property_min_max    = kaa_get_property_min_max;
    this->vo_driver.gui_data_exchange       = kaa_gui_data_exchange;
    this->vo_driver.dispose                 = kaa_dispose;
    this->vo_driver.redraw_needed           = kaa_redraw_needed;

    //this->passthrough           = passthrough;
    this->passthrough           = visual->passthrough;
    this->send_frame_cb         = visual->send_frame_cb;
    this->send_frame_cb_data    = visual->send_frame_cb_data;
    this->osd_buffer            = visual->osd_buffer;
    this->osd_stride            = visual->osd_stride;
    this->osd_rows              = visual->osd_rows;
    this->osd_configure_cb      = visual->osd_configure_cb;
    this->osd_configure_cb_data = visual->osd_configure_cb_data;

    this->send_frame_width      = -1;
    this->send_frame_height     = -1;
    this->yuv2rgb_factory       = yuv2rgb_factory_init(MODE_32_RGB, 0, NULL);
    this->cur_frame             = 0;
    this->do_passthrough        = 1;
    this->do_send_frame         = 0;
    this->osd_visible           = 0;
    this->osd_w                 = -1;
    this->osd_h                 = -1;
    this->osd_alpha             = 255;

    return &this->vo_driver;
}

static char *
kaa_get_identifier(video_driver_class_t *this_gen)
{
    return "kaa";
}

static char *
kaa_get_description(video_driver_class_t *this_gen)
{
    return "Passthrough driver with OSD and buffer output.";
}

static void
kaa_dispose_class(video_driver_class_t *this_gen)
{
    //printf("kaa_dispose_class\n");
    free(this_gen);
}

static void *
kaa_init_class (xine_t *xine, void *visual_gen) 
{
    //printf("kaa_init_class\n");
    kaa_class_t *this;

    this = (kaa_class_t *)xine_xmalloc(sizeof(kaa_class_t));
    init_rgb2yuv_tables();
    premultiply_alpha_byte_8 = premultiply_alpha_byte_8_C;
    blend_plane = blend_plane_C;
#if defined(ARCH_X86) || defined(ARCH_X86_64)
    if (xine_mm_accel() & MM_ACCEL_X86_MMX) {
        premultiply_alpha_byte_8 = premultiply_alpha_byte_8_MMX;
        blend_plane = blend_plane_MMX;
    }
#endif

    this->driver_class.open_plugin      = kaa_open_plugin;
    this->driver_class.get_identifier   = kaa_get_identifier;
    this->driver_class.get_description  = kaa_get_description;
    this->driver_class.dispose          = kaa_dispose_class;

    this->config = xine->config;
    this->xine   = xine;
    return this;
}



static vo_info_t kaa_vo_info = {
    1,
    XINE_VISUAL_TYPE_NONE
};

plugin_info_t xine_vo_kaa_plugin_info[] = {
    { PLUGIN_VIDEO_OUT, 21, "kaa", XINE_VERSION_CODE, &kaa_vo_info, &kaa_init_class },
    { PLUGIN_NONE, 0, "", 0, NULL, NULL }
};


