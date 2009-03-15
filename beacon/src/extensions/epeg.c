/*
 * ----------------------------------------------------------------------------
 * Epeg Thumbnailer
 * ----------------------------------------------------------------------------
 * $Id: libthumb.c 3814 2009-01-24 17:26:22Z dmeyer $
 *
 * Epeg was a fast jpeg thumbnailer created by the Enlightenment
 * project. During its development its functionality was included in
 * evas and epeg was discontinued. But evas is a huge dependency for
 * such a small task like jpeg thumbnailing. This file contains the
 * parts we need from epeg to do the thumbnailing. Unlike
 * Enlightenment we only use epeg to decode the image and not to
 * encode it again. We save as png to be compatible with
 * freedesktop.org.
 *
 * Why we need this?  Well, if we load the image with imlib2 and store
 * as thumbnail, a 10 MP test image here takes 0.78 seconds for this
 * task. Epeg creating a jpeg only takes 0.16 seconds. The compromise
 * we use here (epeg for decoding, libpng for storage) takes 0.19
 * seconds. That is a huge improvement. The second advantage of epeg,
 * having smaller jpeg thumbnails instead of png is not supported. But
 * at least we have speed.
 *
 * ----------------------------------------------------------------------------
 * kaa.beacon - A virtual filesystem with metadata
 * Copyright (C) 2009 Dirk Meyer
 *
 * First Edition: Dirk Meyer <dischi@freevo.org>
 * Maintainer:    Dirk Meyer <dischi@freevo.org>
 *
 * Based on Epeg by
 * The Rasterman (Carsten Haitzler) <raster@rasterman.com>
 * Jerome Foucher <jerome.foucher@mipsys.com>
 * Michal Kowalczuk, Wirtualna Polska <sammael@wp-sa.pl>
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

#include <stdio.h>
#include <unistd.h>
#include <stdlib.h>
#include <string.h>
#include <limits.h>
#include <time.h>
#include <fcntl.h>
#include <sys/types.h>
#include <sys/stat.h>
#include <setjmp.h>
#include <jpeglib.h>
#include <jerror.h>

#include "epeg.h"

typedef struct _epeg_error_mgr *emptr;

struct _epeg_error_mgr
{
      struct     jpeg_error_mgr pub;
      jmp_buf    setjmp_buffer;
};

struct _Epeg_Image
{
   struct _epeg_error_mgr          jerr;
   struct stat                     stat_info;
   unsigned char                  *pixels;
   unsigned char                 **lines;

   char                            scaled : 1;

   int                             error;

   Epeg_Colorspace                 color_space;

   struct {
      char                          *file;
      struct {
	 unsigned char           **data;
	 int                       size;
      } mem;
      int                            w, h;
      FILE                          *f;
      J_COLOR_SPACE                  color_space;
      struct jpeg_decompress_struct  jinfo;
   } in;
   struct {
      int                          x, y;
      int                          w, h;
   } out;
};

static Epeg_Image   *_epeg_open_header         (Epeg_Image *im);
static int           _epeg_decode              (Epeg_Image *im);
static int           _epeg_scale               (Epeg_Image *im);

static void          _epeg_fatal_error_handler (j_common_ptr cinfo);

METHODDEF(void) _jpeg_init_source(j_decompress_ptr cinfo);
METHODDEF(boolean) _jpeg_fill_input_buffer(j_decompress_ptr cinfo);
METHODDEF(void) _jpeg_skip_input_data(j_decompress_ptr cinfo, long num_bytes);
METHODDEF(void) _jpeg_term_source(j_decompress_ptr cinfo);

static const JOCTET fake_EOI[2] = { 0xFF, JPEG_EOI };

/**
 * Open a JPEG image by filename.
 * @param file The file path to open.
 * @return A handle to the opened JPEG file, with the header decoded.
 *
 * This function opens the file indicated by the @p file parameter, and
 * attempts to decode it as a jpeg file. If this failes, NULL is returned.
 * Otherwise a valid handle to an open JPEG file is returned that can be used
 * by other Epeg calls.
 *
 * The @p file must be a pointer to a valid C string, NUL (0 byte) terminated
 * thats is a relative or absolute file path. If not results are not
 * determined.
 *
 * See also: epeg_memory_open(), epeg_close()
 */
Epeg_Image *
epeg_file_open(const char *file)
{
   Epeg_Image *im;

   im = calloc(1, sizeof(Epeg_Image));
   if (!im) return NULL;

   im->in.file = strdup(file);
   if (!im->in.file)
     {
	free(im);
	return NULL;
     }

   im->in.f = fopen(im->in.file, "rb");
   if (!im->in.f)
     {
	epeg_close(im);
	return NULL;
     }
   fstat(fileno(im->in.f), &(im->stat_info));
   return _epeg_open_header(im);
}

/**
 * Open a JPEG image stored in memory.
 * @param data A pointer to the memory containing the JPEG data.
 * @param size The size of the memory segment containing the JPEG.
 * @return  A handle to the opened JPEG, with the header decoded.
 *
 * This function opens a JPEG file that is stored in memory pointed to by
 * @p data, and that is @p size bytes in size. If successful a valid handle
 * is returned, or on failure NULL is returned.
 *
 * See also: epeg_file_open(), epeg_close()
 */
Epeg_Image *
epeg_memory_open(unsigned char *data, int size)
{
   Epeg_Image *im;

   im = calloc(1, sizeof(Epeg_Image));
   if (!im) return NULL;

   im->in.mem.data = (unsigned char **)data;
   im->in.mem.size = size;
   im->in.f = NULL;
   im->in.w = 0;
   im->in.h = 0;
   return _epeg_open_header(im);
}

/**
 * Return the original JPEG pixel size.
 * @param im A handle to an opened Epeg image.
 * @param w A pointer to the width value in pixels to be filled in.
 * @param h A pointer to the height value in pixels to be filled in.
 *
 * Returns the image size in pixels.
 *
 */
void
epeg_size_get(Epeg_Image *im, int *w, int *h)
{
   if (w) *w = im->in.w;
   if (h) *h = im->in.h;
}

/**
 * Return the original JPEG pixel color space.
 * @param im A handle to an opened Epeg image.
 * @param space A pointer to the color space value to be filled in.
 *
 * Returns the image color space.
 *
 */
void
epeg_colorspace_get(Epeg_Image *im, int *space)
{
   if (space) *space = im->color_space;
}

/**
 * Set the size of the image to decode in pixels.
 * @param im A handle to an opened Epeg image.
 * @param w The width of the image to decode at, in pixels.
 * @param h The height of the image to decode at, in pixels.
 *
 * Sets the size at which to deocode the JPEG image, giving an optimised load
 * that only decodes the pixels needed.
 *
 */
void
epeg_decode_size_set(Epeg_Image *im, int w, int h)
{
   if      (im->pixels) return;
   if      (w < 1)        w = 1;
   else if (w > im->in.w) w = im->in.w;
   if      (h < 1)        h = 1;
   else if (h > im->in.h) h = im->in.h;
   im->out.w = w;
   im->out.h = h;
   im->out.x = 0;
   im->out.y = 0;
}

/**
 * Set the colorspace in which to decode the image.
 * @param im A handle to an opened Epeg image.
 * @param colorspace The colorspace to decode the image in.
 *
 * This sets the colorspace to decode the image in. The default is EPEG_YUV8,
 * as this is normally the native colorspace of a JPEG file, avoiding any
 * colorspace conversions for a faster load and/or save.
 */
void
epeg_decode_colorspace_set(Epeg_Image *im, Epeg_Colorspace colorspace)
{
   if (im->pixels) return;
   if ((colorspace < EPEG_GRAY8) || (colorspace > EPEG_ARGB32)) return;
   im->color_space = colorspace;
}

/**
 * Get a segment of decoded pixels from an image.
 * @param im A handle to an opened Epeg image.
 * @param x Rectangle X.
 * @param y Rectangle Y.
 * @param w Rectangle width.
 * @param h Rectangle height.
 * @return Pointer to the top left of the requested pixel block.
 *
 * Return image pixels in the decoded format from the specified location
 * rectangle bounded with the box @p x, @p y @p w X @p y. The pixel block is
 * packed with no row padding, and it organsied from top-left to bottom right,
 * row by row. You must free the pixel block using epeg_pixels_free() before
 * you close the image handle, and assume the pixels to be read-only memory.
 *
 * On success the pointer is returned, on failure, NULL is returned. Failure
 * may be because the rectangle is out of the bounds of the image, memory
 * allocations failed or the image data cannot be decoded.
 *
 */
const void *
epeg_pixels_get(Epeg_Image *im)
{
    int xx, yy, bpp, w, h;
    unsigned int *pix, *p;

    if (!im->pixels)
	{
	    if (_epeg_decode(im) != 0) return NULL;
	}

    if (!im->pixels) return NULL;
    if ((im->out.w < 1) || (im->out.h < 1)) return NULL;
    if (_epeg_scale(im) != 0) return NULL;

    bpp = im->in.jinfo.output_components;
    w = im->out.w;
    h = im->out.h;

    pix = malloc(w * h * 4);
    if (!pix) return NULL;

    for (yy = 0; yy < h; yy++)
	{
	    unsigned char *s;

	    s = im->lines[yy];
	    p = pix + ((((yy) * w)));
	    for (xx = 0; xx < w; xx++)
		{
		    p[0] = 0xff000000 | (s[0] << 16) | (s[1] << 8) | (s[2]);
		    p++;
		    s += bpp;
		}
	}
    return pix;
}

/**
 * Free requested pixel block from an image.
 * @param im A handle to an opened Epeg image.
 * @param data The pointer to the image pixels.
 *
 * This frees the data for a block of pixels requested from image @p im.
 * @p data must be a valid (non NULL) pointer to a pixel block taken from the
 * image @p im by epeg_pixels_get() and mustbe called before the image is
 * closed by epeg_close().
 */
void
epeg_pixels_free(Epeg_Image *im, const void *data)
{
   free((void *)data);
}

/**
 * Close an image handle.
 * @param im A handle to an opened Epeg image.
 *
 * This closes an opened image handle and frees all memory associated
 * with it.  It does not free guarantee to free any data recieved by
 * epeg_pixels_get(). Once an image handle is closed consider it
 * invalid.
 */
void
epeg_close(Epeg_Image *im)
{
   if (!im) return;
   if (im->pixels)                   free(im->pixels);
   if (im->lines)                    free(im->lines);
   if (im->in.file)                  free(im->in.file);
   if (!im->in.file)                 free(im->in.jinfo.src);
   if (im->in.f || im->in.mem.data)  jpeg_destroy_decompress(&(im->in.jinfo));
   if (im->in.f)                     fclose(im->in.f);
   free(im);
}

static Epeg_Image *
_epeg_open_header(Epeg_Image *im)
{
   struct jpeg_source_mgr *src_mgr = NULL;

   im->in.jinfo.err = jpeg_std_error(&(im->jerr.pub));
   im->jerr.pub.error_exit = _epeg_fatal_error_handler;

   if (setjmp(im->jerr.setjmp_buffer))
     {
	error:
	epeg_close(im);
	im = NULL;
	return NULL;
     }

   jpeg_create_decompress(&(im->in.jinfo));
   jpeg_save_markers(&(im->in.jinfo), JPEG_APP0 + 7, 1024);
   jpeg_save_markers(&(im->in.jinfo), JPEG_COM,      65535);
   if (im->in.f != NULL)
     {
	jpeg_stdio_src(&(im->in.jinfo), im->in.f);
     }
   else
     {
	/* Setup RAM source manager. */
	src_mgr = calloc(1, sizeof(struct jpeg_source_mgr));
	if (!src_mgr) goto error;
	src_mgr->init_source = _jpeg_init_source;
	src_mgr->fill_input_buffer = _jpeg_fill_input_buffer;
	src_mgr->skip_input_data = _jpeg_skip_input_data;
	src_mgr->resync_to_restart = jpeg_resync_to_restart;
	src_mgr->term_source = _jpeg_term_source;
	src_mgr->bytes_in_buffer = im->in.mem.size;
	src_mgr->next_input_byte = (JOCTET *) im->in.mem.data;
   	im->in.jinfo.src = (struct jpeg_source_mgr *) src_mgr;
     }

   jpeg_read_header(&(im->in.jinfo), TRUE);
   im->in.w = im->in.jinfo.image_width;
   im->in.h = im->in.jinfo.image_height;
   if (im->in.w < 1) goto error;
   if (im->in.h < 1) goto error;

   im->out.w = im->in.w;
   im->out.h = im->in.h;

   im->color_space = ((im->in.color_space = im->in.jinfo.out_color_space) == JCS_GRAYSCALE) ? EPEG_GRAY8 : EPEG_RGB8;
   if (im->in.color_space == JCS_CMYK) im->color_space = EPEG_CMYK;
   return im;
}

/**
  retval 1 - malloc or other
         2 - setjmp error
*/
static int
_epeg_decode(Epeg_Image *im)
{
   int scale, scalew, scaleh, y;
   JDIMENSION old_output_scanline = 1;

   if (im->pixels) return 1;
   if ((im->out.w < 1) || (im->out.h < 1)) return 1;

   scalew = im->in.w / im->out.w;
   scaleh = im->in.h / im->out.h;

   scale = scalew;
   if (scaleh < scalew) scale = scaleh;

   if      (scale > 8) scale = 8;
   else if (scale < 1) scale = 1;

   im->in.jinfo.scale_num           = 1;
   im->in.jinfo.scale_denom         = scale;
   im->in.jinfo.do_fancy_upsampling = FALSE;
   im->in.jinfo.do_block_smoothing  = FALSE;
   im->in.jinfo.dct_method          = JDCT_IFAST;

   switch (im->color_space)
     {
      case EPEG_GRAY8:
	im->in.jinfo.out_color_space = JCS_GRAYSCALE;
	im->in.jinfo.output_components = 1;
	break;

      case EPEG_YUV8:
	im->in.jinfo.out_color_space = JCS_YCbCr;
	break;

      case EPEG_RGB8:
      case EPEG_BGR8:
      case EPEG_RGBA8:
      case EPEG_BGRA8:
      case EPEG_ARGB32:
	im->in.jinfo.out_color_space = JCS_RGB;
	break;

      case EPEG_CMYK:
	im->in.jinfo.out_color_space = JCS_CMYK;
	im->in.jinfo.output_components = 4;
	break;

      default:
	break;
     }

   if (setjmp(im->jerr.setjmp_buffer))
     return 2;

   jpeg_calc_output_dimensions(&(im->in.jinfo));

   im->pixels = malloc(im->in.jinfo.output_width * im->in.jinfo.output_height * im->in.jinfo.output_components);
   if (!im->pixels) return 1;

   im->lines = malloc(im->in.jinfo.output_height * sizeof(char *));
   if (!im->lines)
     {
	free(im->pixels);
	im->pixels = NULL;
	return 1;
     }

   jpeg_start_decompress(&(im->in.jinfo));

   for (y = 0; y < im->in.jinfo.output_height; y++)
     im->lines[y] = im->pixels + (y * im->in.jinfo.output_components * im->in.jinfo.output_width);

   while (im->in.jinfo.output_scanline < im->in.jinfo.output_height)
     {
	if (old_output_scanline == im->in.jinfo.output_scanline)
	  {
	     jpeg_abort_decompress(&(im->in.jinfo));
	     return 1;
	  }
	old_output_scanline = im->in.jinfo.output_scanline;
	jpeg_read_scanlines(&(im->in.jinfo),
			    &(im->lines[im->in.jinfo.output_scanline]),
			    im->in.jinfo.rec_outbuf_height);
     }

   jpeg_finish_decompress(&(im->in.jinfo));

   return 0;
}

static int
_epeg_scale(Epeg_Image *im)
{
   unsigned char *dst, *row, *src;
   int            x, y, w, h, i;

   if ((im->in.w == im->out.w) && (im->in.h == im->out.h)) return 0;
   if (im->scaled) return 0;

   if ((im->out.w < 1) || (im->out.h < 1)) return 0;

   im->scaled = 1;
   w = im->out.w;
   h = im->out.h;
   for (y = 0; y < h; y++)
     {
	row = im->pixels + (((y * im->in.jinfo.output_height) / h) * im->in.jinfo.output_components * im->in.jinfo.output_width);
	dst = im->pixels + (y * im->in.jinfo.output_components * im->in.jinfo.output_width);

	for (x = 0; x < im->out.w; x++)
	  {
	     src = row + (((x * im->in.jinfo.output_width) / w) * im->in.jinfo.output_components);
	     for (i = 0; i < im->in.jinfo.output_components; i++)
	       dst[i] = src[i];
	     dst += im->in.jinfo.output_components;
	  }
     }
   return 0;
}

METHODDEF(void)
_jpeg_init_source(j_decompress_ptr cinfo)
{
}

METHODDEF(boolean)
_jpeg_fill_input_buffer(j_decompress_ptr cinfo)
{
   WARNMS(cinfo, JWRN_JPEG_EOF);
   
   /* Insert a fake EOI marker */
   cinfo->src->next_input_byte = fake_EOI;
   cinfo->src->bytes_in_buffer = sizeof(fake_EOI);
   return TRUE;
}

METHODDEF(void)
_jpeg_skip_input_data(j_decompress_ptr cinfo, long num_bytes)
{
   if (num_bytes > (long)(cinfo)->src->bytes_in_buffer)
     ERREXIT(cinfo, 0);
   
   (cinfo)->src->next_input_byte += num_bytes;
   (cinfo)->src->bytes_in_buffer -= num_bytes;
}

METHODDEF(void)
_jpeg_term_source(j_decompress_ptr cinfo)
{
}

static void 
_epeg_fatal_error_handler(j_common_ptr cinfo)
{
   emptr errmgr;
   
   errmgr = (emptr)cinfo->err;
   longjmp(errmgr->setjmp_buffer, 1);
   return;
}

