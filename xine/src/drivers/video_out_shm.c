/*
 * ----------------------------------------------------------------------------
 * Video driver for shm.xine - writes frames into shmem buffers
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

#include <math.h>
#include <malloc.h>
#include <assert.h>
#include <pthread.h>
#include <sys/shm.h>
#include <unistd.h>

#include "../config.h"
#include "video_out_shm.h"


static int
check_shmem(shm_driver_t *this, shm_frame_t *frame)
{
    int i, bufsize;
    bufsize = 32 + frame->vo_frame.pitches[0] * frame->height * (frame->format == XINE_IMGFMT_YUY2 ? 1 : 2);
    if (this->bufsize >= bufsize)
        return 0;


    if (this->shm_id) {
        struct shmid_ds shmemds;
        // FIXME: before destroying shmem, verify all buffers are unlocked.
        shmctl(this->shm_id, IPC_RMID, &shmemds);
        shmdt(this->shmem); 
    }
    this->shm_id = shmget(IPC_PRIVATE, bufsize * NUM_BUFFERS, IPC_CREAT | 0600);
    if (this->shm_id == -1) {
        xprintf(this->xine, XINE_VERBOSITY_LOG, "video_out_shm: failed to create shmem segment\n");
        return -1;
    }
    this->shmem = shmat(this->shm_id, NULL, 0);
    for (i = 0; i < NUM_BUFFERS; i++) {
        this->buffers[i] = this->shmem + bufsize * i;
        *this->buffers[i] = 0;
    }
    this->cur_buffer_idx = 0;
    this->bufsize = bufsize;
    return 0;
}

static inline void
wait_for_buffer(uint8_t *lock, float max_wait)
{
    struct timeval curtime;
    double start, now;

    gettimeofday(&curtime, NULL);
    start = now = curtime.tv_sec + (curtime.tv_usec/(1000.0*1000));
    while (*lock && now - start < max_wait) {
        gettimeofday(&curtime, NULL);
        now = curtime.tv_sec + (curtime.tv_usec/(1000.0*1000));
        usleep(1);
    }
}

static uint32_t 
shm_get_capabilities(vo_driver_t *this_gen)
{
    return VO_CAP_YV12 | VO_CAP_YUY2;
}

static void
shm_frame_field(vo_frame_t *frame_gen, int which)
{
}

static void
free_framedata(shm_frame_t *frame)
{
    if (frame->vo_frame.base[0]) {
        free(frame->vo_frame.base[0]);
        frame->vo_frame.base[0] = NULL;
        frame->vo_frame.base[1] = NULL;
        frame->vo_frame.base[2] = NULL;
    }
}


static void
shm_frame_dispose(vo_frame_t *vo_img)
{
    shm_frame_t *frame = (shm_frame_t *)vo_img;
    pthread_mutex_destroy(&frame->vo_frame.mutex);
    free_framedata(frame);
    free(frame);
}


static vo_frame_t *
shm_alloc_frame(vo_driver_t *this_gen)
{
    shm_frame_t *frame;
    shm_driver_t *this = (shm_driver_t *)this_gen;
    
    frame = (shm_frame_t *)xine_xmalloc(sizeof(shm_frame_t));
    if (!frame)
        return NULL;

    pthread_mutex_init(&frame->vo_frame.mutex, NULL);

    frame->vo_frame.base[0] = NULL;
    frame->vo_frame.base[1] = NULL;
    frame->vo_frame.base[2] = NULL;

    frame->vo_frame.proc_slice = NULL;
    frame->vo_frame.proc_frame = NULL;
    frame->vo_frame.field = shm_frame_field;
    frame->vo_frame.dispose = shm_frame_dispose;
    frame->vo_frame.driver = this_gen;
    frame->driver = this;

    return (vo_frame_t *)frame;
}

static void 
shm_update_frame_format (vo_driver_t *this_gen,
                         vo_frame_t *frame_gen,
                         uint32_t width, uint32_t height,
                         double ratio, int format, int flags) 
{
    shm_driver_t *this = (shm_driver_t *)this_gen;
    shm_frame_t *frame = (shm_frame_t *)frame_gen;

    if (frame->width == width && frame->height == height && frame->format == format)
        return;
      
    free_framedata(frame);
    
    frame->width  = width;
    frame->height = height;
    frame->format = format;
    
    /* TODO: investigate using DR here.  NUM_BUFFERS will then need
     * to be dynamic and based on the number of frames allocated before
     * the first display_frame.  But this will only work if new frames will
     * never get allocated after the first display_frame.
     */
    if (format == XINE_IMGFMT_YV12) {
        int y_size, uv_size;
        
        frame->vo_frame.pitches[0] = 8*((width + 7) / 8);
        frame->vo_frame.pitches[1] = 8*((width + 15) / 16);
        frame->vo_frame.pitches[2] = 8*((width + 15) / 16);
        
        y_size  = frame->vo_frame.pitches[0] * height;
        uv_size = frame->vo_frame.pitches[1] * ((height+1)/2);
        
        frame->vo_frame.base[0] = malloc (y_size + 2*uv_size);
        frame->vo_frame.base[1] = frame->vo_frame.base[0]+y_size;
        frame->vo_frame.base[2] = frame->vo_frame.base[0]+y_size+uv_size;
    } else if (format == XINE_IMGFMT_YUY2) {
        frame->vo_frame.pitches[0] = 8*((width + 3) / 4);
        frame->vo_frame.base[0] = malloc(frame->vo_frame.pitches[0] * height);
        frame->vo_frame.base[1] = NULL;
        frame->vo_frame.base[2] = NULL;
    } else
        xprintf(this->xine, XINE_VERBOSITY_LOG, "video_out_shm: unsupported frame format %04x\n", format);
    
    frame->ratio = ratio;
}

static int
shm_redraw_needed(vo_driver_t *vo)
{
    return 0;
}

static void 
shm_display_frame (vo_driver_t *this_gen, vo_frame_t *frame_gen) 
{
    shm_driver_t *this = (shm_driver_t *)this_gen;
    shm_frame_t *frame = (shm_frame_t *)frame_gen;
    uint8_t *lock;
    notify_packet_t notify;
    buffer_header_t header = {
        .lock = 1,
        .width = frame->width,
        .height = frame->height,
        .stride = frame->vo_frame.pitches[0],
        .format = frame->format,
        .aspect = frame->ratio 
    };

    if (check_shmem(this, frame) == -1)
        return;
    lock = this->buffers[this->cur_buffer_idx];
    if (*lock)
        wait_for_buffer(lock, 0.1);

    if (frame->format == XINE_IMGFMT_YV12) {
        xine_fast_memcpy(32 + lock, frame->vo_frame.base[0],
                         (frame->vo_frame.pitches[0] * frame->height) +
                         (frame->vo_frame.pitches[1] * frame->height/2) * 2);
    } 
    else if (frame->format == XINE_IMGFMT_YUY2) {
        xine_fast_memcpy(32 + lock, frame->vo_frame.base[0], frame->vo_frame.pitches[0] * frame->height);
    } 
    xine_fast_memcpy(lock, &header, sizeof(header));

    notify.shm_id = this->shm_id;
    notify.offset = lock - this->buffers[0];
    write(this->fd_notify, &notify, sizeof(notify));
    fsync(this->fd_notify);
    this->cur_buffer_idx++;
    if (this->cur_buffer_idx == NUM_BUFFERS)
        this->cur_buffer_idx = 0;

    frame->vo_frame.free(&frame->vo_frame);
}

static int 
shm_get_property (vo_driver_t *this_gen, int property) 
{
  return 0;
}

static int 
shm_set_property (vo_driver_t *this_gen,
                int property, int value) 
{
    return value;
}

static void 
shm_get_property_min_max (vo_driver_t *this_gen,
                     int property, int *min, int *max) 
{
    //shm_driver_t *this = (shm_driver_t *)this_gen;
    *min = 0;
    *max = 0;
}

static int
shm_gui_data_exchange (vo_driver_t *this_gen,
                 int data_type, void *data) 
{
    //shm_driver_t *this = (shm_driver_t *)this_gen;
    return 0;
}

static void
shm_overlay_begin (vo_driver_t *this_gen,
                  vo_frame_t *frame_gen, int changed)
{
  shm_driver_t  *this  = (shm_driver_t *) this_gen;

  this->alphablend_extra_data.offset_x = frame_gen->overlay_offset_x;
  this->alphablend_extra_data.offset_y = frame_gen->overlay_offset_y;
}


static void
shm_overlay_blend(vo_driver_t *this_gen, vo_frame_t *frame_gen, vo_overlay_t *vo_overlay)
{
    shm_frame_t *frame = (shm_frame_t *)frame_gen;
    shm_driver_t *this = (shm_driver_t *)this_gen;

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
shm_dispose(vo_driver_t *this_gen)
{
    shm_driver_t *this = (shm_driver_t *)this_gen;

    if (this->shm_id) {
        struct shmid_ds shmemds;
        shmctl(this->shm_id, IPC_RMID, &shmemds);
        shmdt(this->shmem);
        this->shmem = 0;
        this->shm_id = 0;
    }

    pthread_mutex_destroy(&this->lock);
    free(this);
}


static vo_driver_t *
shm_open_plugin(video_driver_class_t *class_gen, const void *visual_gen)
{
    shm_class_t *class = (shm_class_t *)class_gen;
    shm_visual_t *visual = (shm_visual_t *)visual_gen;
    shm_driver_t *this;

    this = (shm_driver_t *)xine_xmalloc(sizeof(shm_driver_t));
    memset(this, 0, sizeof(shm_driver_t));
    if (!this)
        return NULL;

    this->xine = class->xine;
    this->config = class->config;
    pthread_mutex_init(&this->lock, NULL);
    
    this->vo_driver.get_capabilities        = shm_get_capabilities;
    this->vo_driver.alloc_frame             = shm_alloc_frame;
    this->vo_driver.update_frame_format     = shm_update_frame_format;
    this->vo_driver.overlay_begin           = shm_overlay_begin;
    this->vo_driver.overlay_blend           = shm_overlay_blend;
    this->vo_driver.overlay_end             = NULL;
    this->vo_driver.display_frame           = shm_display_frame;
    this->vo_driver.get_property            = shm_get_property;
    this->vo_driver.set_property            = shm_set_property;
    this->vo_driver.get_property_min_max    = shm_get_property_min_max;
    this->vo_driver.gui_data_exchange       = shm_gui_data_exchange;
    this->vo_driver.dispose                 = shm_dispose;
    this->vo_driver.redraw_needed           = shm_redraw_needed;

    this->fd_notify = visual->fd_notify;
    this->shmem = 0;
    this->shm_id = 0;
    this->bufsize = 0;
    return &this->vo_driver;
}

static char *
shm_get_identifier(video_driver_class_t *this_gen)
{
    return "shm";
}

static char *
shm_get_description(video_driver_class_t *this_gen)
{
    return "Write video frames to shared memory.";
}

static void
shm_dispose_class(video_driver_class_t *this_gen)
{
    free(this_gen);
}

static void *
shm_init_class (xine_t *xine, void *visual_gen) 
{
    shm_class_t *this;

    this = (shm_class_t *)xine_xmalloc(sizeof(shm_class_t));

    this->driver_class.open_plugin      = shm_open_plugin;
    this->driver_class.get_identifier   = shm_get_identifier;
    this->driver_class.get_description  = shm_get_description;
    this->driver_class.dispose          = shm_dispose_class;

    this->config = xine->config;
    this->xine   = xine;
    return this;
}



static vo_info_t shm_vo_info = {
    1,
    XINE_VISUAL_TYPE_NONE
};

plugin_info_t xine_vo_shm_plugin_info[] = {
    { PLUGIN_VIDEO_OUT, 21, "shm", XINE_VERSION_CODE, &shm_vo_info, &shm_init_class },
    { PLUGIN_NONE, 0, "", 0, NULL, NULL }
};

