#include "video_out_dummy.h"
#include <malloc.h>

static uint32_t 
dummy_get_capabilities(vo_driver_t *this_gen)
{
    printf("dummy: get_capabilities\n");
    return VO_CAP_YV12 | VO_CAP_YUY2;
}

static void
dummy_frame_field(vo_frame_t *frame, int which)
{
    printf("dummy_frame_field %d\n", which);
}

static void
dummy_frame_dispose(vo_frame_t *vo_img)
{
    dummy_frame_t *frame = (dummy_frame_t *)vo_img;
    printf("dummy_frame_dispose\n");
    pthread_mutex_destroy(&frame->vo_frame.mutex);
    free(frame);
}

void dummy_frame_inc_lock(vo_frame_t *img)
{
}

void dummy_frame_dec_lock(vo_frame_t *img)
{
}


static vo_frame_t *
dummy_alloc_frame(vo_driver_t *this_gen)
{
    dummy_frame_t *frame;
    //dummy_driver_t *this = (dummy_driver_t *)this_gen;
    
    printf("dummy_alloc_frame\n");
    frame = (dummy_frame_t *)xine_xmalloc(sizeof(dummy_frame_t));
    if (!frame)
        return NULL;

    pthread_mutex_init(&frame->vo_frame.mutex, NULL);

    frame->vo_frame.base[0] = NULL;
    frame->vo_frame.base[1] = NULL;
    frame->vo_frame.base[2] = NULL;

    frame->vo_frame.proc_slice = NULL;
    frame->vo_frame.proc_frame = NULL;
    frame->vo_frame.field = dummy_frame_field;
    frame->vo_frame.dispose = dummy_frame_dispose;
    frame->vo_frame.driver = this_gen;

    return (vo_frame_t *)frame;
}

static void 
dummy_update_frame_format (vo_driver_t *this_gen, vo_frame_t *frame_gen,
                           uint32_t width, uint32_t height,
                           double ratio, int format, int flags) 
{
    //dummy_driver_t *this = (dummy_driver_t *)this_gen;
    dummy_frame_t *frame = (dummy_frame_t *)frame_gen;

    // Noisy.  This function gets called a lot.  Xine isn't very smart about
    // memory allocation.  Luckily malloc/free is pretty fast.
    // printf("dummy_update_frame_format: %dx%d\n", width, height);


    // XXX: locking in this function risks deadlock!

    // Allocate memory for the desired frame format and size
    if (frame->width != width || frame->height != height || format != frame->format) {
        // Free memory from old frame configuration
        if (frame->vo_frame.base[0])
            free(frame->vo_frame.base[0]);
        if (frame->vo_frame.base[1]) {
            free(frame->vo_frame.base[1]);
            free(frame->vo_frame.base[2]);
        }

        if (format == XINE_IMGFMT_YV12) {
            // Align pitch to 16 byte multiple.
            frame->vo_frame.pitches[0] = (width + 15) & ~15;
            frame->vo_frame.pitches[1] = frame->vo_frame.pitches[0] >> 1;
            frame->vo_frame.pitches[2] = frame->vo_frame.pitches[1];

            frame->vo_frame.base[0] = (uint8_t *)memalign(16, frame->vo_frame.pitches[0] * height);
            frame->vo_frame.base[1] = (uint8_t *)memalign(16, frame->vo_frame.pitches[1] * height);
            frame->vo_frame.base[2] = (uint8_t *)memalign(16, frame->vo_frame.pitches[2] * height);
        } else if (format == XINE_IMGFMT_YUY2) {
            frame->vo_frame.pitches[0] = ((width + 3) & ~3) * 2;
            frame->vo_frame.pitches[1] = 0;
            frame->vo_frame.pitches[2] = 0;

            frame->vo_frame.base[0] = (uint8_t *)memalign(16, frame->vo_frame.pitches[0] * height);
            frame->vo_frame.base[1] = NULL;
            frame->vo_frame.base[2] = NULL;
        }
    }

    frame->width = width;
    frame->height = height;
    frame->format = format;
    frame->ratio = ratio;
    frame->flags = flags;
}

static int
dummy_redraw_needed(vo_driver_t *vo)
{
    //dummy_driver_t *this = (dummy_driver_t *)vo;
    printf("dummy_redraw_needed\n");
    return 0;
}

static void 
dummy_display_frame(vo_driver_t *this_gen, vo_frame_t *frame_gen) 
{
    dummy_driver_t *this = (dummy_driver_t *)this_gen;
    dummy_frame_t *frame = (dummy_frame_t *)frame_gen;

    pthread_mutex_lock(&this->lock);

    // Draw frame to display here ...

    frame->vo_frame.free(&frame->vo_frame);
    pthread_mutex_unlock(&this->lock);

}

static int 
dummy_get_property(vo_driver_t *this_gen, int property) 
{
    //dummy_driver_t *this = (dummy_driver_t *)this_gen;
    printf("dummy_get_property %d\n", property);
    return 0;
}

static int 
dummy_set_property(vo_driver_t *this_gen, int property, int value) 
{
    //dummy_driver_t *this = (dummy_driver_t *)this_gen;
    printf("dummy_set_property %d=%d\n", property, value);
    return 0;
}

static void 
dummy_get_property_min_max(vo_driver_t *this_gen, int property, int *min, int *max) 
{
    //dummy_driver_t *this = (dummy_driver_t *)this_gen;
    printf("dummy_get_property_min_max\n");
}

static int
dummy_gui_data_exchange(vo_driver_t *this_gen, int data_type, void *data) 
{
    //dummy_driver_t *this = (dummy_driver_t *)this_gen;
    printf("dummy_gui_data_exchange data_type=%d\n", data_type);
    return 0;
}

static void
dummy_dispose(vo_driver_t *this_gen)
{
    dummy_driver_t *this = (dummy_driver_t *)this_gen;

    printf("dummy_dispose\n");
    free(this);
}

static void
dummy_overlay_blend(vo_driver_t *this_gen, vo_frame_t *frame_gen, vo_overlay_t *vo_overlay)
{
    //dummy_frame_t *frame = (dummy_frame_t *)frame_gen;

    printf("dummy_overlay_blend\n");
}

static vo_driver_t *
dummy_open_plugin(video_driver_class_t *class_gen, const void *visual_gen)
{
    dummy_class_t *class = (dummy_class_t *)class_gen;
    dummy_visual_t *visual = (dummy_visual_t *)visual_gen;
    dummy_driver_t *this;
    
    printf("dummy_open_plugin\n");
    this = (dummy_driver_t *)xine_xmalloc(sizeof(dummy_driver_t));
    if (!this)
        return NULL;

    this->xine = class->xine;
    this->config = class->config;
    pthread_mutex_init(&this->lock, NULL);
    
    this->vo_driver.get_capabilities        = dummy_get_capabilities;
    this->vo_driver.alloc_frame             = dummy_alloc_frame;
    this->vo_driver.update_frame_format     = dummy_update_frame_format;
    this->vo_driver.overlay_begin           = NULL;
    this->vo_driver.overlay_blend           = dummy_overlay_blend;
    this->vo_driver.overlay_end             = NULL;
    this->vo_driver.display_frame           = dummy_display_frame;
    this->vo_driver.get_property            = dummy_get_property;
    this->vo_driver.set_property            = dummy_set_property;
    this->vo_driver.get_property_min_max    = dummy_get_property_min_max;
    this->vo_driver.gui_data_exchange       = dummy_gui_data_exchange;
    this->vo_driver.dispose                 = dummy_dispose;
    this->vo_driver.redraw_needed           = dummy_redraw_needed;

    this->frobate  = visual->frobate;
    return &this->vo_driver;
}

static char *
dummy_get_identifier(video_driver_class_t *this_gen)
{
    return "dummy";
}

static char *
dummy_get_description(video_driver_class_t *this_gen)
{
    return "Dummy video driver";
}

static void
dummy_dispose_class(video_driver_class_t *this_gen)
{
    printf("dummy_dispose_class\n");
    free(this_gen);
}

static void *
dummy_init_class (xine_t *xine, void *visual_gen) 
{
    printf("dummy_init_class\n");
    dummy_class_t *this;

    this = (dummy_class_t *)xine_xmalloc(sizeof(dummy_class_t));

    this->driver_class.open_plugin      = dummy_open_plugin;
    this->driver_class.get_identifier   = dummy_get_identifier;
    this->driver_class.get_description  = dummy_get_description;
    this->driver_class.dispose          = dummy_dispose_class;

    this->config = xine->config;
    this->xine   = xine;
    return this;
}


static vo_info_t dummy_vo_info = {
    1,
    XINE_VISUAL_TYPE_NONE
};

plugin_info_t xine_vo_dummy_plugin_info[] = {
    { PLUGIN_VIDEO_OUT, 21, "dummy", XINE_VERSION_CODE, &dummy_vo_info, &dummy_init_class },
    { PLUGIN_NONE, 0, "", 0, NULL, NULL }
};


