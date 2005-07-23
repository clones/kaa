#include "buffer.h"

typedef struct post_plugin_buffer_s post_plugin_buffer_t;

typedef struct buffer_parameters_s {
    int ptr;
} buffer_parameters_t;

struct post_plugin_buffer_s {
    post_plugin_t post;

    buffer_parameters_t params;
    xine_post_in_t params_input;

    pthread_mutex_t      lock;

};

START_PARAM_DESCR( buffer_parameters_t )
PARAM_ITEM( POST_PARAM_TYPE_INT, ptr, NULL, 0, 0, 0,
            "Pointer to memory buffer" )
END_PARAM_DESCR( param_descr )


static int 
set_parameters(xine_post_t *this_gen, void *param_gen) 
{
    post_plugin_buffer_t *this = (post_plugin_buffer_t *)this_gen;
    buffer_parameters_t *param = (buffer_parameters_t *)param_gen;

    pthread_mutex_lock(&this->lock);
    memcpy(&this->params, param, sizeof(buffer_parameters_t));
    pthread_mutex_unlock(&this->lock);
    return 1;
}

static int 
get_parameters(xine_post_t *this_gen, void *param_gen) 
{
    post_plugin_buffer_t *this = (post_plugin_buffer_t *)this_gen;
    buffer_parameters_t *param = (buffer_parameters_t *)param_gen;

    memcpy(param, &this->params, sizeof(buffer_parameters_t));
    return 1;
}

static 
xine_post_api_descr_t *get_param_descr (void) {
    return &param_descr;
}

static char 
*get_help() {
  return _("Writes the video to a memory buffer.\n"
           "\n"
           "Parameters\n"
           "  ptr: Pointer to buffer.\n"
         );
}

static xine_post_api_t post_api = {
    set_parameters,
    get_parameters,
    get_param_descr,
    get_help,
};



static int buffer_intercept_frame(post_video_port_t *port, vo_frame_t *frame)
{
    static int active=0;
//      return (frame->format == XINE_IMGFMT_YV12 || frame->format == XINE_IMGFMT_YUY2);
    post_plugin_buffer_t *this = (post_plugin_buffer_t *)port->post;

    pthread_mutex_lock(&this->lock);
    if (!active) {
        //printf("BUFFER plugin intercepting, ptr=%d\n", this->params.ptr);
        active=1;
    }
    printf("BUFFER plugin intercepting, ptr=%d aspect=%f\n", this->params.ptr, frame->ratio);
    pthread_mutex_unlock(&this->lock);
    return 0;
}

static void buffer_dispose(post_plugin_t *this_gen)
{
    post_plugin_buffer_t *this = (post_plugin_buffer_t *)this_gen;
    if (_x_post_dispose(this_gen)) {
        pthread_mutex_destroy(&this->lock);
        free(this);
    }
}

static post_plugin_t *buffer_open_plugin(post_class_t *class_gen, int inputs,
                     xine_audio_port_t **audio_target,
                     xine_video_port_t **video_target)
{
    post_plugin_buffer_t *this = (post_plugin_buffer_t *)xine_xmalloc(sizeof(post_plugin_buffer_t));
    post_in_t *input;
    xine_post_in_t *input_api;
    post_out_t *output;
    post_video_port_t *port;

    if (!this || !video_target || !video_target[0]) {
        free(this);
        return NULL;
    }


    printf("BUFFER INIT video target=%x\n", video_target[0]);
    _x_post_init(&this->post, 0, 1);

    this->params.ptr = 0;

    pthread_mutex_init(&this->lock, NULL);

    port = _x_post_intercept_video_port(&this->post, video_target[0], &input, &output);
    port->intercept_frame = buffer_intercept_frame;

    input_api = &this->params_input;
    input_api->name = "parameters";
    input_api->type = XINE_POST_DATA_PARAMETERS;
    input_api->data = &post_api;
    xine_list_append_content(this->post.input, input_api);

//    input->xine_in.name   = "video";
//    output->xine_out.name = "video passthrough";

    this->post.xine_post.video_input[0] = &port->new_port;
    this->post.dispose = buffer_dispose;
    return (post_plugin_t *)this;
}

static char *buffer_get_identifier(post_class_t *class_gen)
{
    return "buffer";
}

static char *buffer_get_description(post_class_t *class_gen)
{
    return "Output video frame to memory buffer";
}

static void buffer_class_dispose(post_class_t *class_gen)
{
    free(class_gen);
}

void *buffer_init_plugin(xine_t *xine, void *data)
{
    post_class_t *class = (post_class_t *)malloc(sizeof(post_class_t));
    if (!class)
        return NULL;

    class->open_plugin = buffer_open_plugin;
    class->get_identifier = buffer_get_identifier;
    class->get_description = buffer_get_description;
    class->dispose = buffer_class_dispose;

    return class;
}


post_info_t buffer_special_info = { XINE_POST_TYPE_VIDEO_FILTER };

plugin_info_t xine_buffer_plugin_info[] = {
  /* type, API, "name", version, special_info, init_function */
    { PLUGIN_POST, 9, "buffer", XINE_VERSION_CODE, &buffer_special_info, &buffer_init_plugin},
    { PLUGIN_NONE, 0, "", 0, NULL, NULL }
};


