#include <Python.h>
#include "buffer.h"
#include "../xine.h"
#include "../video_port.h"

typedef struct buffer_frame_s {
    vo_frame_t vo_frame;
    int width, height, format;
    double ratio;
    // more
} buffer_frame_t;

typedef struct buffer_driver_s {
    vo_driver_t vo_driver;
    config_values_t *config;
    pthread_mutex_t lock;
    xine_t *xine;

    PyObject *callback;
    xine_video_port_t *passthrough;
} buffer_driver_t;

typedef struct buffer_class_s {
    video_driver_class_t driver_class;
    config_values_t *config;
    xine_t *xine;
} buffer_class_t;


static uint32_t 
buffer_get_capabilities(vo_driver_t *this_gen)
{
    printf("buffer: get_capabilities\n");
    return VO_CAP_YV12;
}

static void
buffer_frame_field(vo_frame_t *frame, int which)
{
    // noop
}

static void
buffer_frame_dispose(vo_frame_t *vo_img)
{
    buffer_frame_t *frame = (buffer_frame_t *)vo_img;
    printf("buffer_frame_dispose\n");
    pthread_mutex_destroy(&frame->vo_frame.mutex);
    if (frame->vo_frame.base[0])
        free(frame->vo_frame.base[0]);
    free(frame);
}

static vo_frame_t *
buffer_alloc_frame(vo_driver_t *this_gen)
{
    buffer_frame_t *frame;
    
    //printf("buffer_alloc_frame\n");
    frame = (buffer_frame_t *)xine_xmalloc(sizeof(buffer_frame_t));
    if (!frame)
        return NULL;

    pthread_mutex_init(&frame->vo_frame.mutex, NULL);

    frame->vo_frame.base[0] = NULL;
    frame->vo_frame.base[1] = NULL;
    frame->vo_frame.base[2] = NULL;

    frame->vo_frame.proc_slice = NULL;
    frame->vo_frame.proc_frame = NULL;
    frame->vo_frame.field = buffer_frame_field;
    frame->vo_frame.dispose = buffer_frame_dispose;
    frame->vo_frame.driver = this_gen;

    return (vo_frame_t *)frame;
}


static void 
buffer_update_frame_format (vo_driver_t *this_gen,
                    vo_frame_t *frame_gen,
                    uint32_t width, uint32_t height,
                    double ratio, int format, int flags) 
{
    buffer_driver_t *this = (buffer_driver_t *)this_gen;
    buffer_frame_t *frame = (buffer_frame_t *)frame_gen;
    int y_size, uv_size;

    //printf("buffer_update_frame_format: %dx%d ratio=%.3f\n", width, height, ratio);

    frame->vo_frame.pitches[0] = width;
    frame->vo_frame.pitches[1] = width>>1;
    frame->vo_frame.pitches[2] = width>>1;

    y_size = frame->vo_frame.pitches[0] * height;
    uv_size = frame->vo_frame.pitches[1] * (height>>1);


    if (frame->width != width || frame->height != height) {
        if (frame->vo_frame.base[0]) {
            free(frame->vo_frame.base[0]);
        }
        frame->vo_frame.base[0] = xine_xmalloc(y_size + (2*uv_size));
        frame->vo_frame.base[1] = frame->vo_frame.base[0] + y_size;
        frame->vo_frame.base[2] = frame->vo_frame.base[0] + y_size + uv_size;
    }

    frame->width = width;
    frame->height = height;
    frame->format = format;
    frame->ratio = ratio;


}

static int
buffer_redraw_needed(vo_driver_t *vo)
{
//    printf("buffer_redraw_needed\n");
    return 0;
}

static void 
buffer_display_frame (vo_driver_t *this_gen, vo_frame_t *frame_gen) 
{
    buffer_driver_t *this = (buffer_driver_t *)this_gen;
    buffer_frame_t *frame = (buffer_frame_t *)frame_gen;
    vo_frame_t *passthrough_frame;
    int do_passthrough = 1;
    PyObject *args, *result;
    PyGILState_STATE gstate;

    pthread_mutex_lock(&this->lock);
//    printf("buffer_display_frame: fd=%d %d\n", this->callback, frame->vo_frame.base[0][2000]);

    gstate = PyGILState_Ensure();
    args = Py_BuildValue("(iidi)", frame->width, frame->height, frame->ratio,
                         (long)frame->vo_frame.base[0]);
    result = PyEval_CallObject(this->callback, args);
    if (result) {
        if (PyInt_Check(result))
            do_passthrough = PyLong_AsLong(result);
            
        Py_DECREF(result);
    } else {
        printf("Exception in buffer callback:\n");
        PyErr_Print();
    }
    Py_DECREF(args);
    PyGILState_Release(gstate);

    if (this->passthrough && do_passthrough) {
        passthrough_frame = this->passthrough->get_frame(this->passthrough, 
            frame->vo_frame.width, frame->vo_frame.height, frame->vo_frame.ratio, 
            frame->vo_frame.format, frame->vo_frame.flags);
        
        int size = (frame_gen->pitches[0] * frame->height) + (frame_gen->pitches[1] * (frame->height>>1))*2;
        xine_fast_memcpy(passthrough_frame->base[0], frame_gen->base[0], frame_gen->pitches[0] * frame->height);
        xine_fast_memcpy(passthrough_frame->base[1], frame_gen->base[1], frame_gen->pitches[1] * (frame->height>>1));
        xine_fast_memcpy(passthrough_frame->base[2], frame_gen->base[2], frame_gen->pitches[2] * (frame->height>>1));

        _x_post_frame_copy_down(frame, passthrough_frame);
        passthrough_frame->draw(passthrough_frame, frame_gen->stream);
        _x_post_frame_copy_up(passthrough_frame, frame);
        passthrough_frame->free(passthrough_frame);
    }
    frame->vo_frame.free(&frame->vo_frame);
    pthread_mutex_unlock(&this->lock);
}

static int 
buffer_get_property (vo_driver_t *this_gen, int property) 
{
    printf("buffer_get_property: %d\n", property);
}

static int 
buffer_set_property (vo_driver_t *this_gen,
                int property, int value) 
{
    printf("buffer_set_property %d=%d\n", property, value);
}

static void 
buffer_get_property_min_max (vo_driver_t *this_gen,
                     int property, int *min, int *max) 
{
    printf("buffer_get_property_min_max\n");
}

static int
buffer_gui_data_exchange (vo_driver_t *this_gen,
                 int data_type, void *data) 
{
    printf("buffer_gui_data_exchange\n");
    return 0;
}

static void
buffer_dispose(vo_driver_t *this_gen)
{
    buffer_driver_t *this = (buffer_driver_t *)this_gen;
    printf("buffer_dispose\n");
    if (this->callback)
       Py_DECREF(this->callback);

    free(this);
    printf("Returning from buffer_dispose\n");
}

static vo_driver_t *
buffer_open_plugin(video_driver_class_t *class_gen, const void *args)
{
    buffer_class_t *class = (buffer_class_t *)class_gen;
    config_values_t *config = class->config;
    buffer_driver_t *this;
    PyObject *kwargs, *callback, *passthrough;
    
    kwargs = (PyObject *)args;
    callback = PyDict_GetItemString(kwargs, "callback");
    if (!callback) {
        PyErr_Format(xine_error, "Specify callback for buffer driver");
        return NULL;
    }
    passthrough = PyDict_GetItemString(kwargs, "passthrough");
    if (passthrough && !Xine_Video_Port_PyObject_Check(passthrough)) {
        PyErr_Format(xine_error, "Passthrough must be a video driver");
        return NULL;
    }

    printf("buffer_open_plugin\n");
    this = (buffer_driver_t *)xine_xmalloc(sizeof(buffer_driver_t));
    if (!this)
        return NULL;

    this->xine = class->xine;
    this->config = class->config;
    pthread_mutex_init(&this->lock, NULL);
    
    this->vo_driver.get_capabilities        = buffer_get_capabilities;
    this->vo_driver.alloc_frame             = buffer_alloc_frame;
    this->vo_driver.update_frame_format     = buffer_update_frame_format;
    this->vo_driver.overlay_begin           = NULL;
    this->vo_driver.overlay_blend           = NULL;
    this->vo_driver.overlay_end             = NULL;
    this->vo_driver.display_frame           = buffer_display_frame;
    this->vo_driver.get_property            = buffer_get_property;
    this->vo_driver.set_property            = buffer_set_property;
    this->vo_driver.get_property_min_max    = buffer_get_property_min_max;
    this->vo_driver.gui_data_exchange       = buffer_gui_data_exchange;
    this->vo_driver.dispose                 = buffer_dispose;
    this->vo_driver.redraw_needed           = buffer_redraw_needed;

    this->callback = callback;
    Py_INCREF(this->callback);
    this->passthrough = ((Xine_Video_Port_PyObject *)passthrough)->vo;

    return &this->vo_driver;
}

static char *
buffer_get_identifier(video_driver_class_t *this_gen)
{
    return "buffer";
}

static char *
buffer_get_description(video_driver_class_t *this_gen)
{
    return "Output frame to memory buffer";
}

static void
buffer_dispose_class(video_driver_class_t *this_gen)
{
    printf("buffer_dispose_class\n");
    free(this_gen);
}

static void *
buffer_init_class (xine_t *xine, void *visual_gen) 
{
    printf("buffer_init_class\n");
    buffer_class_t *this;

    this = (buffer_class_t *)xine_xmalloc(sizeof(buffer_class_t));

    this->driver_class.open_plugin      = buffer_open_plugin;
    this->driver_class.get_identifier   = buffer_get_identifier;
    this->driver_class.get_description  = buffer_get_description;
    this->driver_class.dispose          = buffer_dispose_class;

    this->config = xine->config;
    this->xine   = xine;
    return this;
}

static vo_info_t buffer_vo_info = {
    1,
    XINE_VISUAL_TYPE_NONE
};

plugin_info_t xine_vo_buffer_plugin_info[] = {
    { PLUGIN_VIDEO_OUT, 20, "buffer", XINE_VERSION_CODE, &buffer_vo_info, &buffer_init_class },
    { PLUGIN_NONE, 0, "", 0, NULL, NULL }
};


