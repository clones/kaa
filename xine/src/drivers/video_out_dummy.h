#include <xine.h>
#include <xine/xineutils.h>
#include <xine/xine_plugin.h>
#include <xine/video_out.h>
#include <xine/xine_internal.h>

extern plugin_info_t xine_vo_dummy_plugin_info[];

typedef struct dummy_frame_s {
    vo_frame_t vo_frame;
    int width, height, format, flags;
    double ratio;
} dummy_frame_t;

typedef struct dummy_driver_s {
    vo_driver_t vo_driver;
    config_values_t *config;
    pthread_mutex_t lock;
    xine_t *xine;

    int frobate;
} dummy_driver_t;


typedef struct dummy_class_s {
    video_driver_class_t driver_class;
    config_values_t *config;
    xine_t *xine;
} dummy_class_t;


typedef struct dummy_visual_s {
    int frobate;
} dummy_visual_t;
