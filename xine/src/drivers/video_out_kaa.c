#include <math.h>
#include "../config.h"
#include "video_out_kaa.h"

static int _kaa_blend_osd(kaa_driver_t *this, kaa_frame_t *frame);
#define STOPWATCH

#ifdef STOPWATCH
static void stopwatch(int n, char *text, ...)
{
    va_list ap;
    struct timezone tz;
    static struct {
        struct timeval tv, last_tv;
        char text[250];
    } t[10];

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
        this->osd_pre_alpha_planes, this->osd_pre_alpha_planes, NULL
    };

    for (p = 0; planes[p] != NULL; p++) {
        for (i = 0; i < 3; i++) {
            if (planes[p][i] && i < 2)
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
        printf("ALLOC OSD for YV12\n");
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
    }
    else if (format == XINE_IMGFMT_YUY2) {
        printf("YUY2 frame format not yet implemented\n");
        this->osd_format = 0;
    } else {
        printf("ERROR: unsupported frame format; osd disabled.\n");
        this->osd_format = 0;
    }

    this->osd_format = format;
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
    int global_alpha = this->osd_alpha;
    uint8_t *y_ptr, *u_ptr, *v_ptr, *a_ptr, *uva_ptr,
            *pre_y_ptr, *pre_u_ptr, *pre_v_ptr, *pre_a_ptr, *pre_uva_ptr;
    int luma_offset, chroma_offset;
    unsigned int x, y, chroma_stride;

    stopwatch(2, "premultiply_alpha (%d,%d %dx%d)", rx, ry, rw, rh);

    if (global_alpha > 255)
        global_alpha = 255;

    luma_offset = rx + ry * this->osd_w;
    chroma_offset = (rx >> 1) + (ry >> 1) * (this->osd_w >> 1);

    y_ptr = this->osd_planes[0] + luma_offset;
    u_ptr = this->osd_planes[1] + chroma_offset;
    v_ptr = this->osd_planes[2] + chroma_offset;
    a_ptr = this->osd_alpha_planes[0] + luma_offset;
    uva_ptr = this->osd_alpha_planes[1] + chroma_offset;

    pre_y_ptr = this->osd_pre_planes[0]+ luma_offset;
    pre_u_ptr = this->osd_pre_planes[1] + chroma_offset;
    pre_v_ptr = this->osd_pre_planes[2] + chroma_offset;
    pre_a_ptr = this->osd_pre_alpha_planes[0] + luma_offset;
    pre_uva_ptr = this->osd_pre_alpha_planes[1] + chroma_offset;

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

    chroma_stride = this->osd_w >> 1;
    for (y = 0; y < rh; y += 2) {
        for (x = 0; x < rw; x += 8)
            premultiply_alpha_byte_8(&y_ptr[x], &a_ptr[x], &pre_y_ptr[x], &pre_a_ptr[x], global_alpha);
        for (; x < rw; x++)
            premultiply_alpha_byte(y_ptr[x], a_ptr[x], &pre_y_ptr[x], &pre_a_ptr[x], global_alpha);

        for (x = 0; x < (rw >> 1); x += 8) {
            premultiply_alpha_byte_8(&u_ptr[x], &uva_ptr[x], &pre_u_ptr[x], &pre_uva_ptr[x], global_alpha);
            premultiply_alpha_byte_8(&v_ptr[x], &uva_ptr[x], &pre_v_ptr[x], &pre_uva_ptr[x], global_alpha);
        }
        for (; x < rw >> 1; x++) {
            premultiply_alpha_byte(u_ptr[x], uva_ptr[x], &pre_u_ptr[x], &pre_uva_ptr[x], global_alpha);
            premultiply_alpha_byte(v_ptr[x], uva_ptr[x], &pre_v_ptr[x], &pre_uva_ptr[x], global_alpha);
        }
        y_ptr += this->osd_w;
        u_ptr += chroma_stride;
        v_ptr += chroma_stride;
        a_ptr += this->osd_w;
        uva_ptr += chroma_stride;

        pre_y_ptr += this->osd_w;
        pre_u_ptr += chroma_stride;
        pre_v_ptr += chroma_stride;
        pre_a_ptr += this->osd_w;
        pre_uva_ptr += chroma_stride;

        for (x = 0; x < rw; x += 8)
            premultiply_alpha_byte_8(&y_ptr[x], &a_ptr[x], &pre_y_ptr[x], &pre_a_ptr[x], global_alpha);
        for (; x < rw; x++)
            premultiply_alpha_byte(y_ptr[x], a_ptr[x], &pre_y_ptr[x], &pre_a_ptr[x], global_alpha);

        y_ptr += this->osd_w;
        a_ptr += this->osd_w;
        pre_y_ptr += this->osd_w;
        pre_a_ptr += this->osd_w;
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
    int y, c = w / 8,
        stride_diff = frame_stride - overlay_stride;

    for (y = 0; y < slice_h; y++) {
        if (c) {
            asm volatile(
                ".balign 16 \n\t"
                "mov %4, %%"REG_c"\n\t"

                "1: \n\t"
                "movq (%1), %%mm0\n\t"        // %mm0 = mpi
                "movq %%mm0, %%mm1\n\t"       // %mm1 = mpi
                "movq (%3), %%mm2\n\t"        // %mm2 = %mm3 = 255 - alpha
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
                "movq (%2), %%mm2\n\t"        // %mm2 = src image (overlay)
                "packuswb %%mm1, %%mm0\n\t"
                "paddb %%mm2, %%mm0\n\t"
                "movq %%mm0, (%0)\n\t"        // Store to dst (mpi)

                "add $8, %0\n\t"
                "add $8, %1\n\t"
                "add $8, %2\n\t"
                "add $8, %3\n\t"
                "decl %%"REG_c"\n\t"
                "jnz 1b \n\t"

            : "+r" (dst),
              "+r" (src),
              "+r" (overlay),
              "+r" (alpha)
            : "m" (c)
            : "%"REG_c);
        }
        // Blend the last few pixels of this row ...
        if (w % 8) {
            uint8_t *end = dst + (w % 8);
            for (; dst < end; dst++, src++, alpha++, overlay++)
                *dst = blend_byte(*src, *overlay, *alpha);
        }
        // If the frame is bigger than overlay, move the frame buffers into
        // the right position for the next row.
        if (stride_diff > 0) {
            dst += stride_diff;
            src += stride_diff;
        }
        // Likewise for overlay if the overlay is bigger than frame.
        else if (stride_diff < 0) {
            overlay += abs(stride_diff);
            alpha += abs(stride_diff);
        }
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
    int slice_y, slice_h, w, i, c, plane, overlay_stride[3];
    uint8_t *dst_frame_planes[3], *src_frame_planes[3], *overlay, *src, *dst, *alpha,
            *overlay_planes[3], *alpha_planes[3];

    // Clip the slice to the frame image.
    slice_y = this->osd_slice_y;
    slice_h = this->osd_slice_h;

    if (slice_y < 0)
        slice_y = 0;
    else if (slice_y > frame->height)
        slice_y = frame->height;

    if (slice_h < 0)
        slice_h = 0;
    else if (slice_h > frame->height - slice_y)
        slice_h = frame->height - slice_y;


    stopwatch(2, "blend_image (0,%d, %dx%d)",  slice_y, this->osd_w, slice_h);

    for (i = 0, c = 0; i < 3; i++, c = 1)  {
        // Setup buffer positions for overlay, mpi src and mpi dst.
        overlay_planes[i] = this->osd_pre_planes[i];
        alpha_planes[i] = this->osd_pre_alpha_planes[i];
        overlay_stride[i] = this->osd_w >> c;
        dst_frame_planes[i] = frame->base[i] + ((slice_y >> c) * frame->pitches[i]);
        src_frame_planes[i] = frame->base[i] + ((slice_y >> c) * frame->pitches[i]);
        overlay_planes[i] += (slice_y >> c) * (this->osd_w >> c);
        alpha_planes[i] += (slice_y >> c) * (this->osd_w >> c);

/*
        if (src_mpi == dst_mpi)
            continue;

        // If we're compositing only a slice, copy the parts of the mpi
        // above and below the slice.
        if (slice_y > 0)
            memcpy(dst_mpi->planes[i], src_mpi->planes[i], src_mpi->stride[i] * slice_y >> c);
        if (slice_h >= 0 && slice_y + slice_h < src_mpi->height)
            memcpy(dst_mpi->planes[i] + dst_mpi->stride[i] * ((slice_y+slice_h) >> c),
                   src_mpi->planes[i] + src_mpi->stride[i] * ((slice_y+slice_h) >> c),
                   src_mpi->stride[i] * (src_mpi->height-(slice_y+slice_h)) >> c);
*/
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

    for (w = this->osd_w, plane = 0; plane < 3; plane++) {
        if (plane == 1) {
            w >>= 1;
            slice_h >>= 1;
        }
        overlay = overlay_planes[plane];
        alpha = alpha_planes[plane];
        src = src_frame_planes[plane];
        dst = dst_frame_planes[plane];

        // Global alpha is 256 which means ignore per-pixel alpha. Do
        // straight memcpy.
//        if (this->osd_alpha == 256) {
 //           memcpy_pic(dst, overlay, w, slice_h, dst_mpi->stride[plane], src_mpi->stride[plane]);
  //      } else {
            blend_plane(w, slice_h, dst, src, overlay, alpha,
                        frame->pitches[plane], overlay_stride[plane]);
   //     }
    }
#if defined(ARCH_X86) || defined(ARCH_X86_64)
    if (xine_mm_accel() & MM_ACCEL_X86_MMX)
        asm volatile( "emms\n\t" ::: "memory" );
#endif
    stopwatch(2, NULL);
}








//////////////////////////////////////




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

////////////

static uint32_t 
kaa_get_capabilities(vo_driver_t *this_gen)
{
    kaa_driver_t *this = (kaa_driver_t *)this_gen;
    printf("kaa: get_capabilities\n");
    return VO_CAP_YV12 | VO_CAP_YUY2;
}

static void
kaa_frame_field(vo_frame_t *frame_gen, int which)
{
    kaa_frame_t *frame = (kaa_frame_t *)frame_gen;
    printf("kaa_frame_field %d\n", which);
    frame->passthrough_frame->field(frame->passthrough_frame, which);
}

static void
kaa_frame_proc_slice(vo_frame_t *frame_gen, uint8_t **src)
{
    kaa_frame_t *frame = (kaa_frame_t *)frame_gen;
    printf("kaa_frame_proc_slice: %x %d %d,%d %x %x %x (crop %d %d %d %d)\n", frame, frame_gen->proc_called, frame->width, frame->height, src[0], src[1], src[2], frame->vo_frame.crop_left, frame->vo_frame.crop_top, frame->vo_frame.crop_right, frame->vo_frame.crop_bottom);
    //memset(src[0], 255, frame->width * frame->height);
    //_kaa_blend_osd(frame->driver, frame);
//    int *a=0;
 //   printf("%d\n", *a);
    frame->passthrough_frame->proc_slice(frame->passthrough_frame, src);
    frame_gen->proc_called = 1;
}

static void
kaa_frame_proc_frame(vo_frame_t *frame_gen)
{
    kaa_frame_t *frame = (kaa_frame_t *)frame_gen;
    printf("kaa_frame_proc_frame\n");
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
    if (frame->yuy2_buffer)
        free(frame->yuy2_buffer);
    if (frame->bgra_buffer)
        free(frame->bgra_buffer);

//    if (frame->passthrough_frame)
//        frame->passthrough_frame->dispose(frame->passthrough_frame);
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
    
    printf("kaa_alloc_frame: %x\n", this);
    frame = (kaa_frame_t *)xine_xmalloc(sizeof(kaa_frame_t));
    if (!frame)
        return NULL;

    pthread_mutex_init(&frame->vo_frame.mutex, NULL);
    pthread_mutex_init(&frame->bgra_lock, NULL);

    frame->yv12_buffer = frame->yuy2_buffer = frame->bgra_buffer = NULL;

    frame->vo_frame.base[0] = NULL;
    frame->vo_frame.base[1] = NULL;
    frame->vo_frame.base[2] = NULL;


    frame->passthrough_frame = this->passthrough->alloc_frame(this->passthrough);
    frame->passthrough_frame->free = vo_frame_dec_lock;
    frame->passthrough_frame->lock = vo_frame_inc_lock;

//    if (frame->passthrough_frame->proc_slice)
 //      frame->vo_frame.proc_slice = kaa_frame_proc_slice;
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
    //int y_size, uv_size;

    //printf("kaa_update_frame_format: %x format=%d  %dx%d\n", frame, format, width, height);
    // XXX: locking in this function risks deadlock.

    frame_gen->proc_called=0;
    this->passthrough->update_frame_format(this->passthrough,
        frame->passthrough_frame, width, height, ratio, format, flags);

    memcpy(&frame->vo_frame.pitches, frame->passthrough_frame->pitches, sizeof(int)*3);
    memcpy(&frame->vo_frame.base, frame->passthrough_frame->base, sizeof(char *)*3);
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
    if (frame->width != this->osd_w || frame->height != this->osd_h) {
        this->osd_w = frame->width;
        this->osd_h = frame->height;
        this->osd_slice_h = frame->height;
        if (this->osd_configure_cb) {
            alloc_overlay_data(this, frame->format);
            this->osd_configure_cb(frame->width, frame->height, frame->ratio, this->osd_configure_cb_data);
            convert_bgra_to_yv12a(this, 0, 0, frame->width, frame->height);
            image_premultiply_alpha(this, 0, 0, frame->width, frame->height);
        }
    } else if (frame->format != this->osd_format) {
        alloc_overlay_data(this, frame->format);
        printf("OSD: TODO: frame format change\n");
    }
    if (this->osd_visible) 
        blend_image(this, &frame->vo_frame);

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
/*
    switch(property) {
        case VO_PROP_ASPECT_RATIO:
            return this->aspect;
    }
*/
    return this->passthrough->get_property(this->passthrough, property);
}

static int 
kaa_set_property (vo_driver_t *this_gen,
                int property, int value) 
{
    kaa_driver_t *this = (kaa_driver_t *)this_gen;
    printf("kaa_set_property %d=%d\n", property, value);
/*
    switch (property) {
        case VO_PROP_ASPECT_RATIO:
            if (value >= XINE_VO_ASPECT_NUM_RATIOS)
                value = XINE_VO_ASPECT_AUTO;
            this->aspect = value;
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
    printf("kaa_get_property_min_max\n");
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
            break;
        }
    }
    return this->passthrough->gui_data_exchange(this->passthrough, data_type, data);
}

static void
kaa_dispose(vo_driver_t *this_gen)
{
    kaa_driver_t *this = (kaa_driver_t *)this_gen;

    printf("kaa_dispose\n");
    this->yuv2rgb_factory->dispose(this->yuv2rgb_factory);
    free_overlay_data(this);
    free(this);
}

static vo_driver_t *
kaa_open_plugin(video_driver_class_t *class_gen, const void *visual_gen)
{
    kaa_class_t *class = (kaa_class_t *)class_gen;
    kaa_visual_t *visual = (kaa_visual_t *)visual_gen;
    kaa_driver_t *this;
    
    printf("kaa_open_plugin\n");
    this = (kaa_driver_t *)xine_xmalloc(sizeof(kaa_driver_t));
    memset(this, 0, sizeof(kaa_driver_t));
    if (!this)
        return NULL;

    this->xine = class->xine;
    this->config = class->config;
    pthread_mutex_init(&this->lock, NULL);
    
    this->vo_driver.get_capabilities        = kaa_get_capabilities;
    this->vo_driver.alloc_frame             = kaa_alloc_frame;
    this->vo_driver.update_frame_format     = kaa_update_frame_format;
    this->vo_driver.overlay_begin           = NULL;
    this->vo_driver.overlay_blend           = _overlay_blend;
    this->vo_driver.overlay_end             = NULL;
    this->vo_driver.display_frame           = kaa_display_frame;
    this->vo_driver.get_property            = kaa_get_property;
    this->vo_driver.set_property            = kaa_set_property;
    this->vo_driver.get_property_min_max    = kaa_get_property_min_max;
    this->vo_driver.gui_data_exchange       = kaa_gui_data_exchange;
    this->vo_driver.dispose                 = kaa_dispose;
    this->vo_driver.redraw_needed           = kaa_redraw_needed;

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
    this->last_frame            = 0;
    this->do_passthrough        = 1;
    this->do_send_frame         = 0;
    this->osd_visible           = 0;
    this->osd_w                 = -1;
    this->osd_h                 = -1;
    this->osd_alpha             = 190;

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
    printf("kaa_dispose_class\n");
    free(this_gen);
}

static void *
kaa_init_class (xine_t *xine, void *visual_gen) 
{
    printf("kaa_init_class\n");
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


// These rle blend functions taken from xine (src/video_out/alphablend.c)

#define BLEND_BYTE(dst, src, o) (((src)*o + ((dst)*(0xf-o)))/0xf)

static void mem_blend32(uint8_t *mem, uint8_t *src, uint8_t o, int len) {
  uint8_t *limit = mem + len*4;
  while (mem < limit) {
    *mem = BLEND_BYTE(*mem, src[0], o);
    mem++;
    *mem = BLEND_BYTE(*mem, src[1], o);
    mem++;
    *mem = BLEND_BYTE(*mem, src[2], o);
    mem++;
    *mem = BLEND_BYTE(*mem, src[3], o);
    mem++;
  }
}


typedef struct {         /* CLUT == Color LookUp Table */
  uint8_t cb    : 8;
  uint8_t cr    : 8;
  uint8_t y     : 8;
  uint8_t foo   : 8;
} __attribute__ ((packed)) clut_t;


static void _overlay_mem_blend_8(uint8_t *mem, uint8_t val, uint8_t o, size_t sz)
{
   uint8_t *limit = mem + sz;
   while (mem < limit) {
      *mem = BLEND_BYTE(*mem, val, o);
      mem++;
   }
}

static void _overlay_blend_yuv(uint8_t *dst_base[3], vo_overlay_t * img_overl, int dst_width, int dst_height, int dst_pitches[3])
{
   clut_t *my_clut;
   uint8_t *my_trans;
   int src_width;
   int src_height;
   rle_elem_t *rle;
   rle_elem_t *rle_limit;
   int x_off;
   int y_off;
   int ymask, xmask;
   int rle_this_bite;
   int rle_remainder;
   int rlelen;
   int x, y;
   int clip_right;
   uint8_t clr = 0;

   src_width = img_overl->width;
   src_height = img_overl->height;
   rle = img_overl->rle;
   rle_limit = rle + img_overl->num_rle;
   x_off = img_overl->x;
   y_off = img_overl->y;

   if (!rle) return;

   //printf("_overlay_blend_yuv: rle=%x w=%d h=%d x=%d y=%d\n", rle, src_width, src_height, x_off, y_off);
   uint8_t *dst_y = dst_base[0] + dst_pitches[0] * y_off + x_off;
   uint8_t *dst_cr = dst_base[2] + (y_off / 2) * dst_pitches[1] + (x_off / 2) + 1;
   uint8_t *dst_cb = dst_base[1] + (y_off / 2) * dst_pitches[2] + (x_off / 2) + 1;
   my_clut = (clut_t *) img_overl->clip_color;
   my_trans = img_overl->clip_trans;

   /* avoid wraping overlay if drawing to small image */
   if( (x_off + img_overl->clip_right) < dst_width )
     clip_right = img_overl->clip_right;
   else
     clip_right = dst_width - 1 - x_off;

   /* avoid buffer overflow */
   if( (src_height + y_off) >= dst_height )
     src_height = dst_height - 1 - y_off;

   rlelen=rle_remainder=0;
   for (y = 0; y < src_height; y++) {
      ymask = ((img_overl->clip_top > y) || (img_overl->clip_bottom < y));
      xmask = 0;

      for (x = 0; x < src_width;) {
     uint16_t o;

     if (rlelen == 0) {
        rle_remainder = rlelen = rle->len;
        clr = rle->color;
        rle++;
     }
     if (rle_remainder == 0) {
        rle_remainder = rlelen;
     }
     if ((rle_remainder + x) > src_width) {
        /* Do something for long rlelengths */
        rle_remainder = src_width - x;
     }

     if (ymask == 0) {
        if (x <= img_overl->clip_left) {
           /* Starts outside clip area */
           if ((x + rle_remainder - 1) > img_overl->clip_left ) {
          /* Cutting needed, starts outside, ends inside */
          rle_this_bite = (img_overl->clip_left - x + 1);
          rle_remainder -= rle_this_bite;
          rlelen -= rle_this_bite;
          my_clut = (clut_t *) img_overl->color;
          my_trans = img_overl->trans;
          xmask = 0;
           } else {
          /* no cutting needed, starts outside, ends outside */
          rle_this_bite = rle_remainder;
          rle_remainder = 0;
          rlelen -= rle_this_bite;
          my_clut = (clut_t *) img_overl->color;
          my_trans = img_overl->trans;
          xmask = 0;
           }
        } else if (x < clip_right) {
           /* Starts inside clip area */
           if ((x + rle_remainder) > clip_right ) {
          /* Cutting needed, starts inside, ends outside */
          rle_this_bite = (clip_right - x);
          rle_remainder -= rle_this_bite;
          rlelen -= rle_this_bite;
          my_clut = (clut_t *) img_overl->clip_color;
          my_trans = img_overl->clip_trans;
          xmask++;
           } else {
          /* no cutting needed, starts inside, ends inside */
          rle_this_bite = rle_remainder;
          rle_remainder = 0;
          rlelen -= rle_this_bite;
          my_clut = (clut_t *) img_overl->clip_color;
          my_trans = img_overl->clip_trans;
          xmask++;
           }
        } else if (x >= clip_right) {
           /* Starts outside clip area, ends outsite clip area */
           if ((x + rle_remainder ) > src_width ) {
          /* Cutting needed, starts outside, ends at right edge */
          /* It should never reach here due to the earlier test of src_width */
          rle_this_bite = (src_width - x );
          rle_remainder -= rle_this_bite;
          rlelen -= rle_this_bite;
          my_clut = (clut_t *) img_overl->color;
          my_trans = img_overl->trans;
          xmask = 0;
           } else {
          /* no cutting needed, starts outside, ends outside */
          rle_this_bite = rle_remainder;
          rle_remainder = 0;
          rlelen -= rle_this_bite;
          my_clut = (clut_t *) img_overl->color;
          my_trans = img_overl->trans;
          xmask = 0;
           }
        }
     } else {
        /* Outside clip are due to y */
        /* no cutting needed, starts outside, ends outside */
        rle_this_bite = rle_remainder;
        rle_remainder = 0;
        rlelen -= rle_this_bite;
        my_clut = (clut_t *) img_overl->color;
        my_trans = img_overl->trans;
        xmask = 0;
     }
     o   = my_trans[clr];
     if (o) {
        if(o >= 15) {
           memset(dst_y + x, my_clut[clr].y, rle_this_bite);
           if (y & 1) {
          memset(dst_cr + (x >> 1), my_clut[clr].cr, (rle_this_bite+1) >> 1);
          memset(dst_cb + (x >> 1), my_clut[clr].cb, (rle_this_bite+1) >> 1);
           }
        } else {
           _overlay_mem_blend_8(dst_y + x, my_clut[clr].y, o, rle_this_bite);
           if (y & 1) {
          /* Blending cr and cb should use a different function, with pre -128 to each sample */
          _overlay_mem_blend_8(dst_cr + (x >> 1), my_clut[clr].cr, o, (rle_this_bite+1) >> 1);
          _overlay_mem_blend_8(dst_cb + (x >> 1), my_clut[clr].cb, o, (rle_this_bite+1) >> 1);
           }
        }

     }
     x += rle_this_bite;
     if (rle >= rle_limit) {
        break;
     }
      }
      if (rle >= rle_limit) {
     break;
      }

      dst_y += dst_pitches[0];

      if (y & 1) {
     dst_cr += dst_pitches[2];
     dst_cb += dst_pitches[1];
      }
   }
}


void _overlay_blend_yuy2 (uint8_t * dst_img, vo_overlay_t * img_overl,
                 int dst_width, int dst_height, int dst_pitch)
{
  clut_t *my_clut;
  uint8_t *my_trans;

  int src_width = img_overl->width;
  int src_height = img_overl->height;
  rle_elem_t *rle = img_overl->rle;
  rle_elem_t *rle_limit = rle + img_overl->num_rle;
  int x_off = img_overl->x;
  int y_off = img_overl->y;
  int x_odd = x_off & 1;
  int ymask;
  int rle_this_bite;
  int rle_remainder;
  int rlelen;
  int x, y;
  int l = 0;
  int clip_right;

  union {
    uint32_t value;
    uint8_t  b[4];
    uint16_t h[2];
  } yuy2;

  uint8_t clr = 0;

  uint8_t *dst_y = dst_img + dst_pitch * y_off + 2 * x_off;
  uint8_t *dst;

  my_clut = (clut_t*) img_overl->clip_color;
  my_trans = img_overl->clip_trans;

  /* avoid wraping overlay if drawing to small image */
  if( (x_off + img_overl->clip_right) <= dst_width )
    clip_right = img_overl->clip_right;
  else
    clip_right = dst_width - x_off;

  /* avoid buffer overflow */
  if( (src_height + y_off) > dst_height )
    src_height = dst_height - y_off;

  if (src_height <= 0)
    return;

  rlelen=rle_remainder=0;
  for (y = 0; y < src_height; y++) {
    if (rle >= rle_limit)
      break;
    
    ymask = ((y < img_overl->clip_top) || (y >= img_overl->clip_bottom));

    dst = dst_y;
    for (x = 0; x < src_width;) {
      uint16_t o;

      if (rle >= rle_limit)
        break;
    
      if ((rlelen < 0) || (rle_remainder < 0)) {
      } 
      if (rlelen == 0) {
        rle_remainder = rlelen = rle->len;
        clr = rle->color;
        rle++;
      }
      if (rle_remainder == 0) {
        rle_remainder = rlelen;
      }
      if ((rle_remainder + x) > src_width) {
        /* Do something for long rlelengths */
        rle_remainder = src_width - x;
      }

      if (ymask == 0) {
        if (x < img_overl->clip_left) { 
          /* Starts outside clip area */
          if ((x + rle_remainder) > img_overl->clip_left ) {
            /* Cutting needed, starts outside, ends inside */
            rle_this_bite = (img_overl->clip_left - x);
            rle_remainder -= rle_this_bite;
            rlelen -= rle_this_bite;
            my_clut = (clut_t*) img_overl->color;
            my_trans = img_overl->trans;
          } else {
          /* no cutting needed, starts outside, ends outside */
            rle_this_bite = rle_remainder;
            rle_remainder = 0;
            rlelen -= rle_this_bite;
            my_clut = (clut_t*) img_overl->color;
            my_trans = img_overl->trans;
          }
        } else if (x < clip_right) {
          /* Starts inside clip area */
          if ((x + rle_remainder) > clip_right ) {
            /* Cutting needed, starts inside, ends outside */
            rle_this_bite = (clip_right - x);
            rle_remainder -= rle_this_bite;
            rlelen -= rle_this_bite;
            my_clut = (clut_t*) img_overl->clip_color;
            my_trans = img_overl->clip_trans;
          } else {
          /* no cutting needed, starts inside, ends inside */
            rle_this_bite = rle_remainder;
            rle_remainder = 0;
            rlelen -= rle_this_bite;
            my_clut = (clut_t*) img_overl->clip_color;
            my_trans = img_overl->clip_trans;
          }
        } else if (x >= clip_right) {
          /* Starts outside clip area, ends outsite clip area */
          if ((x + rle_remainder ) > src_width ) { 
            /* Cutting needed, starts outside, ends at right edge */
            /* It should never reach here due to the earlier test of src_width */
            rle_this_bite = (src_width - x );
            rle_remainder -= rle_this_bite;
            rlelen -= rle_this_bite;
            my_clut = (clut_t*) img_overl->color;
            my_trans = img_overl->trans;
          } else {
          /* no cutting needed, starts outside, ends outside */
            rle_this_bite = rle_remainder;
            rle_remainder = 0;
            rlelen -= rle_this_bite;
            my_clut = (clut_t*) img_overl->color;
            my_trans = img_overl->trans;
          }
        }
      } else {
        /* Outside clip are due to y */
        /* no cutting needed, starts outside, ends outside */
        rle_this_bite = rle_remainder;
        rle_remainder = 0;
        rlelen -= rle_this_bite;
        my_clut = (clut_t*) img_overl->color;
        my_trans = img_overl->trans;
      }
      o   = my_trans[clr];

      if (x < (dst_width - x_off)) {
        /* clip against right edge of destination area */
        if ((x + rle_this_bite) > (dst_width - x_off)) {
          int toClip = (x + rle_this_bite) - (dst_width - x_off);
          
          rle_this_bite -= toClip;
          rle_remainder += toClip;
          rlelen += toClip;
        }

        if (o) {
            l = rle_this_bite>>1;
            if( !((x_odd+x) & 1) ) {
              yuy2.b[0] = my_clut[clr].y;
              yuy2.b[1] = my_clut[clr].cb;
              yuy2.b[2] = my_clut[clr].y;
              yuy2.b[3] = my_clut[clr].cr;
            } else {
              yuy2.b[0] = my_clut[clr].y;
              yuy2.b[1] = my_clut[clr].cr;
              yuy2.b[2] = my_clut[clr].y;
              yuy2.b[3] = my_clut[clr].cb;
            }

          if (o >= 15) {
              while(l--) {
                *(uint16_t *)dst = yuy2.h[0];
                dst += 2;
                *(uint16_t *)dst = yuy2.h[1];
                dst += 2;
              }
              if(rle_this_bite & 1) {
                *(uint16_t *)dst = yuy2.h[0];
                dst += 2;
              }
          } else {
              if( l ) {
                mem_blend32(dst, &yuy2.b[0], o, l);
                dst += 4*l;
              }
              
              if(rle_this_bite & 1) {
                *dst = BLEND_BYTE(*dst, yuy2.b[0], o);
                dst++;
                *dst = BLEND_BYTE(*dst, yuy2.b[1], o);
                dst++;
              }
          }

        } else {
          dst += rle_this_bite*2;
        }
      }
      
      x += rle_this_bite;
    }
    
    dst_y += dst_pitch;
  }
}


static void
_overlay_blend(vo_driver_t *this_gen, vo_frame_t *frame_gen, vo_overlay_t *vo_overlay)
{
    kaa_frame_t *frame = (kaa_frame_t *)frame_gen;

    //printf("kaa_overlay_blend: format=%d overlay=%x\n", frame->format, vo_overlay);
    if (frame->format == XINE_IMGFMT_YV12)
       _overlay_blend_yuv(frame->vo_frame.base, vo_overlay,
                      frame->width, frame->height,
                      frame->vo_frame.pitches);
    else
       _overlay_blend_yuy2(frame->vo_frame.base[0], vo_overlay,
                      frame->width, frame->height,
                      frame->vo_frame.pitches[0]);
}

static vo_info_t kaa_vo_info = {
    1,
    XINE_VISUAL_TYPE_NONE
};

plugin_info_t xine_vo_kaa_plugin_info[] = {
    { PLUGIN_VIDEO_OUT, 20, "kaa", XINE_VERSION_CODE, &kaa_vo_info, &kaa_init_class },
    { PLUGIN_NONE, 0, "", 0, NULL, NULL }
};


