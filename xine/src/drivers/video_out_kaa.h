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

#include <xine.h>
#include <xine/xineutils.h>
#include <xine/xine_plugin.h>
#include <xine/video_out.h>
#include <xine/xine_internal.h>
#include <xine/alphablend.h>
#include "yuv2rgb.h"

extern plugin_info_t xine_vo_kaa_plugin_info[];

#define GUI_SEND_KAA_VO_SET_PASSTHROUGH         1002
#define GUI_SEND_KAA_VO_OSD_SET_VISIBILITY      1010
#define GUI_SEND_KAA_VO_OSD_SET_ALPHA           1011
#define GUI_SEND_KAA_VO_OSD_INVALIDATE_RECT     1012
//#define GUI_SEND_KAA_VO_OSD_SET_SLICE           1013

#define KAA_VO_HANDLE_FRAME_ALLOC               1
#define KAA_VO_HANDLE_FRAME_UPDATE              2
#define KAA_VO_HANDLE_FRAME_DISPOSE             3
#define KAA_VO_HANDLE_FRAME_DISPLAY_PRE_OSD     4
#define KAA_VO_HANDLE_FRAME_DISPLAY_POST_OSD    5


// From mplayer
#if defined(__CYGWIN__) || defined(__MINGW32__) || defined(__OS2__) || \
   (defined(__OpenBSD__) && !defined(__ELF__))
#define MANGLE(a) "_" #a
#else
#define MANGLE(a) #a
#endif


typedef struct kaa_frame_s {
    vo_frame_t vo_frame;
    struct kaa_driver_s *driver;
    int width, height, format;
    double ratio;
    int flags;

    vo_frame_t *passthrough_frame;
    void *user_data;
} kaa_frame_t;

typedef struct kaa_driver_s {
    vo_driver_t vo_driver;
    config_values_t *config;
    pthread_mutex_t lock;
    xine_t *xine;

    kaa_frame_t *last_frame;
    vo_driver_t *passthrough;
    alphablend_t alphablend_extra_data;
    int aspect, needs_redraw, do_passthrough;

    // Custom frame handlers
    int (*handle_frame_cb)(int cmd, vo_frame_t *frame, void **frame_user_data, void *data);
    void *handle_frame_cb_data;

    // OSD members
    void (*osd_configure_cb)(int width, int height, double aspect, void *data, 
                             uint8_t **buffer_return, int *buffer_stride_return);
    uint8_t *osd_configure_cb_data;

    int osd_alpha, osd_visible, osd_slice_y, osd_slice_h;
    uint8_t *osd_buffer;
    int osd_stride, osd_format, osd_w, osd_h;
    
    uint8_t *osd_planes[3], *osd_alpha_planes[3],
            *osd_pre_planes[3], *osd_pre_alpha_planes[3];
    uint16_t osd_strides[3];
    pthread_mutex_t osd_buffer_lock;
    //

} kaa_driver_t;


typedef struct kaa_class_s {
    video_driver_class_t driver_class;
    config_values_t *config;
    xine_t *xine;
} kaa_class_t;


typedef struct kaa_visual_s {
    char *passthrough_driver;
    int passthrough_visual_type;
    void *passthrough_visual;
    vo_driver_t *passthrough;

    void (*osd_configure_cb)(int width, int height, double aspect, void *data, 
                             uint8_t **buffer_return, int *buffer_stride_return);
    void *osd_configure_cb_data;

    int (*handle_frame_cb)(int cmd, vo_frame_t *frame, void **frame_user_data, void *data);
    void *handle_frame_cb_data;
} kaa_visual_t;
