/*
 * ----------------------------------------------------------------------------
 * Video driver for kaa.xine - writes frames into shmem buffers
 * ----------------------------------------------------------------------------
 * $Id$
 *
 * ----------------------------------------------------------------------------
 * Copyright (C) 2008 Jason Tackaberry <tack@urandom.ca>
 *
 * Maintainer:    Jason Tackaberry <tack@urandom.ca>
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

#include "../config.h"
#include <xine.h>
#include <xine/xineutils.h>
#include <xine/xine_plugin.h>
#include <xine/video_out.h>
#include <xine/xine_internal.h>
#include <xine/alphablend.h>

extern plugin_info_t xine_vo_shm_plugin_info[];

#define NUM_BUFFERS 3

typedef struct shm_frame_s {
    vo_frame_t vo_frame;
    struct shm_driver_s *driver;
    uint32_t width, height, format;
    double ratio;
    uint32_t flags;

    void *user_data;
} shm_frame_t;

typedef struct shm_driver_s {
    vo_driver_t vo_driver;
    config_values_t *config;
    pthread_mutex_t lock;
    xine_t *xine;

    alphablend_t alphablend_extra_data;

    uint32_t shm_id, cur_buffer_idx, fd_notify;
    uint8_t *shmem, *buffers[NUM_BUFFERS];
    uint32_t bufsize;
} shm_driver_t;


typedef struct shm_class_s {
    video_driver_class_t driver_class;
    config_values_t *config;
    xine_t *xine;
} shm_class_t;


typedef struct shm_visual_s {
    int fd_notify;
} shm_visual_t;

typedef struct {
    uint8_t lock;
    uint16_t width, height, stride;
    uint32_t format;
    double aspect;
} buffer_header_t;

typedef struct {
    uint32_t shm_id, offset;
    uint8_t padding[8];
} notify_packet_t;

