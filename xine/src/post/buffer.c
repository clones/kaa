#include <Python.h>
#include "buffer.h"

typedef struct post_plugin_buffer_s post_plugin_buffer_t;

typedef struct buffer_parameters_s {
    int callback;
} buffer_parameters_t;

struct post_plugin_buffer_s {
    post_plugin_t post;

    buffer_parameters_t params;
    xine_post_in_t params_input;

    unsigned char *frame_buffer;
    int frame_buffer_size;
    pthread_mutex_t      lock;

};

START_PARAM_DESCR( buffer_parameters_t )
PARAM_ITEM( POST_PARAM_TYPE_INT, callback, NULL, 0, 0, 0,
            "Python callback when new frame is available" )
END_PARAM_DESCR( param_descr )


static int 
set_parameters(xine_post_t *this_gen, void *param_gen) 
{
    post_plugin_buffer_t *this = (post_plugin_buffer_t *)this_gen;
    buffer_parameters_t *param = (buffer_parameters_t *)param_gen;

    pthread_mutex_lock(&this->lock);
    if (this->params.callback)
        Py_DECREF((PyObject *)this->params.callback);
    if (param->callback)
        Py_INCREF((PyObject *)param->callback);
    memcpy(&this->params, param, sizeof(buffer_parameters_t));
    pthread_mutex_unlock(&this->lock);
    return -1;
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
           "  callback: Python callback function on new frame.\n"
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
    return (frame->format == XINE_IMGFMT_YV12);
}


static int buffer_draw(vo_frame_t *frame, xine_stream_t *stream)
{
    post_video_port_t *port = (post_video_port_t *)frame->port;
    post_plugin_buffer_t *this = (post_plugin_buffer_t *)port->post;
    PyGILState_STATE gstate;
    PyObject *args, *result, *callback;
    int bufsize, skip;

    if (!this->params.callback)
        goto end;

    pthread_mutex_lock(&this->lock);

    bufsize = (frame->pitches[0] + frame->pitches[1] + frame->pitches[2]) * frame->height;
    if (bufsize != this->frame_buffer_size) {
        if (this->frame_buffer)
            free(this->frame_buffer);
        this->frame_buffer = (unsigned char *)malloc(bufsize);
        this->frame_buffer_size = bufsize;
    }
    memcpy(this->frame_buffer, frame->base[0], frame->pitches[0] * frame->height);
    memcpy(&this->frame_buffer[frame->pitches[0] * frame->height], 
           frame->base[1], frame->pitches[1] * (frame->height >> 1));
    memcpy(&this->frame_buffer[(frame->pitches[0] * frame->height) + (frame->pitches[1] * (frame->height>>1))],
           frame->base[2], frame->pitches[2] * (frame->height >> 1));
    //memset(this->frame_buffer, 255, bufsize);
    
    gstate = PyGILState_Ensure();
    callback = (PyObject *)this->params.callback;
    args = Py_BuildValue("(iidii)", frame->width, frame->height, frame->ratio, 
                        (long)this->frame_buffer, this->frame_buffer_size);
    result = PyEval_CallObject(callback, args);
    if (result)
        Py_DECREF(result);
    else {
        printf("Exception in buffer callback:\n");
        PyErr_Print();
    }
    Py_DECREF(args);
    PyGILState_Release(gstate);
    pthread_mutex_unlock(&this->lock);

end:
    _x_post_frame_copy_down(frame, frame->next);
    skip = frame->next->draw(frame->next, stream);
    _x_post_frame_copy_up(frame, frame->next);

    printf("Skip: %d\n", skip);
    return skip;
}



static void buffer_dispose(post_plugin_t *this_gen)
{
    post_plugin_buffer_t *this = (post_plugin_buffer_t *)this_gen;
    if (_x_post_dispose(this_gen)) {
        if (this->frame_buffer)
            free(this->frame_buffer);
        if (this->params.callback)
            Py_DECREF((PyObject *)this->params.callback);
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

    this->params.callback = 0;

    this->frame_buffer = 0;
    this->frame_buffer_size = 0;

    pthread_mutex_init(&this->lock, NULL);

    port = _x_post_intercept_video_port(&this->post, video_target[0], &input, &output);
    port->intercept_frame = buffer_intercept_frame;
    port->new_frame->draw = buffer_draw;

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


