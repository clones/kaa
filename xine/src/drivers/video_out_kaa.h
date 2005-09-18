#include <xine.h>
#include <xine/xineutils.h>
#include <xine/xine_plugin.h>
#include <xine/video_out.h>
#include <xine/xine_internal.h>
#include "yuv2rgb.h"

extern plugin_info_t xine_vo_kaa_plugin_info[];

#define GUI_SEND_KAA_VO_SET_SEND_FRAME          1001
#define GUI_SEND_KAA_VO_SET_PASSTHROUGH         1002
#define GUI_SEND_KAA_VO_SET_SEND_FRAME_SIZE     1003
#define GUI_SEND_KAA_VO_SET_OSD_VISIBILITY      1010
#define GUI_SEND_KAA_VO_SET_OSD_ALPHA           1011
#define GUI_SEND_KAA_VO_SET_OSD_SHMKEY          1012


typedef struct kaa_frame_s {
    vo_frame_t vo_frame;
    int width, height, format;
    double ratio;
    int flags;

    unsigned char *yv12_buffer,
                  *yv12_planes[3],
                  *yuy2_buffer,
                  *bgra_buffer;
    int yv12_strides[3];
    pthread_mutex_t bgra_lock;
    vo_frame_t *passthrough_frame;
    yuv2rgb_t *yuv2rgb;
} kaa_frame_t;

typedef struct kaa_driver_s {
    vo_driver_t vo_driver;
    config_values_t *config;
    pthread_mutex_t lock;
    xine_t *xine;

    vo_driver_t *passthrough;

    yuv2rgb_factory_t *yuv2rgb_factory;
    int aspect, do_passthrough, needs_redraw,
        do_send_frame, send_frame_width, send_frame_height;

    void (*send_frame_cb)(int width, int height, double aspect, uint8_t *buffer, pthread_mutex_t *buffer_lock, void *data);
    void *send_frame_cb_data;

    // OSD attributes
    int osd_alpha, osd_visible, osd_shm_key, osd_shm_id;
    

    kaa_frame_t *last_frame;
} kaa_driver_t;


typedef struct kaa_class_s {
    video_driver_class_t driver_class;
    config_values_t *config;
    xine_t *xine;
} kaa_class_t;


typedef struct kaa_visual_s {
    void (*send_frame_cb)(int width, int height, double aspect, uint8_t *buffer, pthread_mutex_t *buffer_lock, void *data);
    void *send_frame_cb_data;
    vo_driver_t *passthrough;
    int osd_shm_key;
} kaa_visual_t;

static void _overlay_blend(vo_driver_t *, vo_frame_t *, vo_overlay_t *);
