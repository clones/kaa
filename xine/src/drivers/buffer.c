#include <Python.h>
#include "buffer.h"
#include "../xine.h"
#include "../vo_driver.h"
#include "yuv2rgb.h"
#include "../config.h"

#define STOPWATCH

#define BUFFER_VO_COMMAND_QUERY_REQUEST 0
#define BUFFER_VO_COMMAND_QUERY_REDRAW  1
#define BUFFER_VO_COMMAND_SEND          2

#define BUFFER_VO_REQUEST_SEND          0x01
#define BUFFER_VO_REQUEST_PASSTHROUGH   0x02


#if defined(ARCH_X86) || defined(ARCH_X86_64)
    #define YUY2_SIZE_THRESHOLD   400*280
#else
    #define YUY2_SIZE_THRESHOLD   2000*2000
#endif




static void _overlay_blend(vo_driver_t *, vo_frame_t *, vo_overlay_t *);

typedef struct buffer_frame_s {
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
    // more
} buffer_frame_t;

typedef struct buffer_driver_s {
    vo_driver_t vo_driver;
    config_values_t *config;
    pthread_mutex_t lock;
    xine_t *xine;

    yuv2rgb_factory_t *yuv2rgb_factory;
    int aspect;

    PyObject *callback;
    vo_driver_t *passthrough;
    PyObject *passthrough_pyobject;
} buffer_driver_t;

typedef struct buffer_class_s {
    video_driver_class_t driver_class;
    config_values_t *config;
    xine_t *xine;
} buffer_class_t;


#ifdef STOPWATCH
static void stopwatch(int n, char *text, ...)
{
    va_list ap;
    struct timezone tz;
    static struct {
        struct timeval tv, last_tv;
        char text[250];
    } t[10];

    gettimeofday(&t[n].tv, &tz);
    if (!text) {
        fprintf(stderr, "@@@ Stopwatch (%d): %s: %ld usec\n", n, t[n].text,
               (t[n].tv.tv_sec - t[n].last_tv.tv_sec) * 1000000 +
               (t[n].tv.tv_usec - t[n].last_tv.tv_usec));
    } else {
        t[n].last_tv.tv_sec = t[n].tv.tv_sec;
        t[n].last_tv.tv_usec = t[n].tv.tv_usec;

        va_start(ap, text);
        vsprintf(t[n].text, text, ap);
        va_end(ap);
    }
}
#else
#define stopwatch(n, text, ...)
#endif


////////////


PyObject *
_unlock_frame_cb(PyObject *self, PyObject *args, PyObject *kwargs)
{
    buffer_frame_t *frame = (buffer_frame_t *)PyCObject_AsVoidPtr(self);
    pthread_mutex_unlock(&frame->bgra_lock);
    Py_INCREF(Py_None);
    return Py_None;
}

PyMethodDef unlock_frame_def = {
    "unlock_frame_cb", (PyCFunction)_unlock_frame_cb, 
    METH_VARARGS, NULL 
};


static int
buffer_callback_command_query_redraw(buffer_driver_t *this)
{
    PyObject *args, *result;
    PyGILState_STATE gstate;
    int retval = 0;

    gstate = PyGILState_Ensure();
    args = Py_BuildValue("(i())", BUFFER_VO_COMMAND_QUERY_REDRAW);
    result = PyEval_CallObject(this->callback, args);
    if (result) {
        if (PyInt_Check(result))
            retval = PyLong_AsLong(result);
        Py_DECREF(result);
    }
    if (PyErr_Occurred()) {
        printf("Exception in buffer callback:\n");
        PyErr_Print();
    }
    Py_DECREF(args);
    PyGILState_Release(gstate);
    return retval;
}

static int
buffer_callback_command_query_request(buffer_driver_t *this, buffer_frame_t *frame,
    int *request_return, int *width_return, int *height_return)
{
    PyObject *args, *result;
    PyGILState_STATE gstate;
    int retval = 1;

    gstate = PyGILState_Ensure();
    args = Py_BuildValue("(i(iid))", BUFFER_VO_COMMAND_QUERY_REQUEST,
                         frame->width, frame->height, frame->ratio);
    result = PyEval_CallObject(this->callback, args);
    if (result) {
        PyArg_ParseTuple(result, "iii", request_return, width_return, height_return);
        Py_DECREF(result);
    }
    if (PyErr_Occurred()) {
        printf("Exception in buffer callback:\n");
        PyErr_Print();
        retval = 0;
    }
    Py_DECREF(args);
    PyGILState_Release(gstate);

    return retval;
}

static int
buffer_callback_send(buffer_driver_t *this, buffer_frame_t *frame, int w, int h)
{
    PyObject *args, *result, *unlock_frame_cb, *frame_pyobject;
    PyGILState_STATE gstate;
    int retval = 1;

    gstate = PyGILState_Ensure();
    frame_pyobject = PyCObject_FromVoidPtr((void *)frame, NULL);
    unlock_frame_cb = PyCFunction_New(&unlock_frame_def, frame_pyobject);
    args = Py_BuildValue("(i(iidiO))", BUFFER_VO_COMMAND_SEND, w, h, 
                         frame->ratio, (long)frame->bgra_buffer, 
                         unlock_frame_cb);
    Py_DECREF(unlock_frame_cb);
    Py_DECREF(frame_pyobject);
    result = PyEval_CallObject(this->callback, args);
    if (result)
        Py_DECREF(result);
    else {
        printf("Exception in buffer callback:\n");
        PyErr_Print();
        retval = 0;
    }
    Py_DECREF(args);
    PyGILState_Release(gstate);

    return retval;
}


////////////


int
pthread_mutex_lock_timeout(pthread_mutex_t *lock, double timeout)
{
    struct timespec abstime;
    abstime.tv_sec = (int)floor(timeout);
    abstime.tv_nsec = (timeout-(double)abstime.tv_sec)*1000000000;
    //printf("Lock timeout: %d sec %d usec\n", abstime.tv_sec, abstime.tv_nsec);
    return pthread_mutex_timedlock(lock, &abstime);
}


static void
_alloc_yv12(int width, int height, unsigned char **base, 
            unsigned char *planes[3], int strides[3])
{
    int y_size, uv_size;

    strides[0] = 8*((width + 7) / 8);
    strides[1] = 8*((width + 15) / 16);
    strides[2] = 8*((width + 15) / 16);
    
    y_size  = strides[0] * height;
    uv_size = strides[1] * ((height+1)/2);
 
    if (*base)
        free(*base);
           
    *base = (unsigned char *)xine_xmalloc(y_size + 2*uv_size);
    
    planes[0] = *base;
    planes[1] = *base + y_size + uv_size;
    planes[2] = *base + y_size;
}

////////////

static uint32_t 
buffer_get_capabilities(vo_driver_t *this_gen)
{
    printf("buffer: get_capabilities\n");
    return VO_CAP_YV12 | VO_CAP_YUY2;
}

static void
buffer_frame_field(vo_frame_t *frame, int which)
{
    printf("frame_field %d\n", which);
    // noop
}

static void
buffer_frame_dispose(vo_frame_t *vo_img)
{
    buffer_frame_t *frame = (buffer_frame_t *)vo_img;
    //printf("buffer_frame_dispose\n");
    pthread_mutex_destroy(&frame->vo_frame.mutex);
    pthread_mutex_destroy(&frame->bgra_lock);
    if (frame->yv12_buffer)
        free(frame->yv12_buffer);
    if (frame->yuy2_buffer)
        free(frame->yuy2_buffer);
    if (frame->bgra_buffer)
        free(frame->bgra_buffer);
    frame->yuv2rgb->dispose (frame->yuv2rgb);
    free(frame);
}

void vo_frame_inc_lock(vo_frame_t *img)
{
}

void vo_frame_dec_lock(vo_frame_t *img)
{
}


static vo_frame_t *
buffer_alloc_frame(vo_driver_t *this_gen)
{
    buffer_frame_t *frame;
    buffer_driver_t *this = (buffer_driver_t *)this_gen;
    
    printf("buffer_alloc_frame: %x\n", this);
    frame = (buffer_frame_t *)xine_xmalloc(sizeof(buffer_frame_t));
    if (!frame)
        return NULL;

    pthread_mutex_init(&frame->vo_frame.mutex, NULL);
    pthread_mutex_init(&frame->bgra_lock, NULL);

    frame->yv12_buffer = frame->yuy2_buffer = frame->bgra_buffer = NULL;

    frame->vo_frame.base[0] = NULL;
    frame->vo_frame.base[1] = NULL;
    frame->vo_frame.base[2] = NULL;

    frame->vo_frame.proc_slice = NULL;
    frame->vo_frame.proc_frame = NULL;
    frame->vo_frame.field = buffer_frame_field;
    frame->vo_frame.dispose = buffer_frame_dispose;
    frame->vo_frame.driver = this_gen;

    frame->passthrough_frame = this->passthrough->alloc_frame(this->passthrough);
    frame->passthrough_frame->free = vo_frame_dec_lock;
    frame->passthrough_frame->lock = vo_frame_inc_lock;

    frame->yuv2rgb = this->yuv2rgb_factory->create_converter(this->yuv2rgb_factory);

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

    //printf("buffer_update_frame_format: %x format=%d  %dx%d\n", frame, format, width, height);

    // XXX: locking in this function risks deadlock.

    this->passthrough->update_frame_format(this->passthrough,
        frame->passthrough_frame, width, height, ratio, format, flags);

    memcpy(&frame->vo_frame.pitches, frame->passthrough_frame->pitches, sizeof(int)*3);
    memcpy(&frame->vo_frame.base, frame->passthrough_frame->base, sizeof(char *)*3);

#if 0
    if (frame->width != width || frame->height != height || format != frame->format) {
        if (format == XINE_IMGFMT_YV12) {
            frame->vo_frame.pitches[0] = 8*((width + 7) / 8);
            frame->vo_frame.pitches[1] = 8*((width + 15) / 16);
            frame->vo_frame.pitches[2] = 8*((width + 15) / 16);
    
            y_size  = frame->vo_frame.pitches[0] * height;
            uv_size = frame->vo_frame.pitches[1] * ((height+1)/2);
    
            if (frame->yv12_buffer && (width != frame->width || height != frame->height)) {
                free(frame->yv12_buffer);
                frame->yv12_buffer = NULL;
            }
            if (!frame->yv12_buffer) {
                printf("buffer_update_frame_format: %x format=%d  %dx%d\n", frame, format, width, height);
                frame->yv12_buffer = xine_xmalloc(y_size + 2*uv_size);
            }
            frame->vo_frame.base[0] = frame->yv12_buffer;
            frame->vo_frame.base[1] = frame->vo_frame.base[0] + y_size+uv_size;
            frame->vo_frame.base[2] = frame->vo_frame.base[0] + y_size;
        } else if (format == XINE_IMGFMT_YUY2) {
            frame->vo_frame.pitches[0] = 8*((width + 3) / 4);
            frame->vo_frame.pitches[1] = 0;
            frame->vo_frame.pitches[2] = 0;
            if (frame->yuy2_buffer && (width != frame->width || height != frame->height)) {
                free(frame->yuy2_buffer);
                frame->yuy2_buffer = NULL;
            }
            if (!frame->yuy2_buffer) {
                printf("buffer_update_frame_format: %x format=%d  %dx%d\n", frame, format, width, height);
                frame->yuy2_buffer = xine_xmalloc(frame->vo_frame.pitches[0] * height);
            }
    
            frame->vo_frame.base[0] = frame->yuy2_buffer;
            frame->vo_frame.base[1] = NULL;
            frame->vo_frame.base[2] = NULL;
        } else {
            printf("\n\n\nUNSUPPORTED FRAME FORMAT %d\n\n\n", format);
        }
    }
#endif
    frame->width = width;
    frame->height = height;
    frame->format = format;
    frame->ratio = ratio;
    frame->flags = flags;
}

static int
buffer_redraw_needed(vo_driver_t *vo)
{
    buffer_driver_t *this = (buffer_driver_t *)vo;
    int redraw;

    redraw = buffer_callback_command_query_redraw(this);
    //printf("buffer_redraw_needed: %d\n", redraw);
    return redraw || this->passthrough->redraw_needed(this->passthrough);
}

static void 
buffer_display_frame (vo_driver_t *this_gen, vo_frame_t *frame_gen) 
{
    buffer_driver_t *this = (buffer_driver_t *)this_gen;
    buffer_frame_t *frame = (buffer_frame_t *)frame_gen;
    vo_frame_t *passthrough_frame;
    int request = 0, dst_width = -1, dst_height = -1;
    PyGILState_STATE gstate;

    //printf("buffer_display_frame: %x draw=%x w=%d h=%d ratio=%.3f format=%d (yv12=%d yuy=%d)\n", frame, frame_gen->draw, frame->vo_frame.width, frame->height, frame->ratio, frame->format, XINE_IMGFMT_YV12, XINE_IMGFMT_YUY2);
    pthread_mutex_lock(&this->lock);

    buffer_callback_command_query_request(this, frame, &request, &dst_width, &dst_height);
    if (dst_width == -1 || dst_height == -1) {
        dst_width = frame->width;
        dst_height = frame->height;
    }

    if (request & BUFFER_VO_REQUEST_SEND) {
        if (pthread_mutex_lock_timeout(&frame->bgra_lock, 0.2) != 0) {
            printf("FAILED to acquire lock\n");
            goto bail;
        }
        if (!frame->bgra_buffer || 
             frame->width != frame->yuv2rgb->source_width || 
             frame->height != frame->yuv2rgb->source_height ||
             frame->vo_frame.pitches[0] != frame->yuv2rgb->y_stride ||
             frame->vo_frame.pitches[1] != frame->yuv2rgb->uv_stride ||
             frame->yuv2rgb->dest_width != dst_width ||
             frame->yuv2rgb->dest_height != dst_height) {

            int y_stride = frame->vo_frame.pitches[0],
                uv_stride = frame->vo_frame.pitches[1];
            if (frame->bgra_buffer)
                free(frame->bgra_buffer);
            frame->bgra_buffer = malloc(frame->width*frame->height*4);

            if (frame->format == XINE_IMGFMT_YUY2 && dst_width*dst_height > YUY2_SIZE_THRESHOLD) {
                _alloc_yv12(frame->width, frame->height, &frame->yv12_buffer,
                            frame->yv12_planes, frame->yv12_strides);
                y_stride = frame->yv12_strides[0];
                uv_stride = frame->yv12_strides[1];
            }

            frame->yuv2rgb->configure(frame->yuv2rgb, frame->width, frame->height,
                                      y_stride, uv_stride,
                                      dst_width, dst_height, 4*(dst_width));
        }
        if (frame->format == XINE_IMGFMT_YV12) {
            stopwatch(0, "yv12 to bgra32");
            frame->yuv2rgb->yuv2rgb_fun (frame->yuv2rgb, frame->bgra_buffer,
                                         frame->vo_frame.base[0],  
                                         frame->vo_frame.base[1],  
                                         frame->vo_frame.base[2]);
            stopwatch(0, NULL);
        } else {
            stopwatch(0, "yuy2 to bgra32");
            if (dst_width*dst_height > YUY2_SIZE_THRESHOLD) {
                // Naive optimization: yuv2rgb has an accelerated version
                // but yuy22rgb doesn't.  So when the area of the image is
                // greater than the size threshold (determined empirically)
                // first convert the yuy2 image to yv12 and then convert
                // yv12 to rgb, both operations of which are accelerated.
                yuy2_to_yv12(frame->vo_frame.base[0], frame->vo_frame.pitches[0],
                             frame->yv12_planes[0], frame->yv12_strides[0],
                             frame->yv12_planes[1], frame->yv12_strides[1],
                             frame->yv12_planes[2], frame->yv12_strides[2],
                             frame->width, frame->height);
                frame->yuv2rgb->yuv2rgb_fun (frame->yuv2rgb, frame->bgra_buffer,
                                             frame->yv12_planes[0],
                                             frame->yv12_planes[1],
                                             frame->yv12_planes[2]);
            } else {
                frame->yuv2rgb->yuy22rgb_fun (frame->yuv2rgb, frame->bgra_buffer,
                                              frame->vo_frame.base[0]);
            }
            stopwatch(0, NULL);
        }
        buffer_callback_send(this, frame, dst_width, dst_height);
    }

bail:
    if (this->passthrough && request & BUFFER_VO_REQUEST_PASSTHROUGH) {
        this->passthrough->display_frame(this->passthrough, frame->passthrough_frame);
    }

    frame->vo_frame.free(&frame->vo_frame);
    pthread_mutex_unlock(&this->lock);

}

static int 
buffer_get_property (vo_driver_t *this_gen, int property) 
{
    buffer_driver_t *this = (buffer_driver_t *)this_gen;
    printf("buffer_get_property: %d\n", property);
    switch(property) {
        case VO_PROP_ASPECT_RATIO:
            return this->aspect;
    }
    return this->passthrough->get_property(this->passthrough, property);
}

static int 
buffer_set_property (vo_driver_t *this_gen,
                int property, int value) 
{
    buffer_driver_t *this = (buffer_driver_t *)this_gen;
    printf("buffer_set_property %d=%d\n", property, value);
    switch (property) {
        case VO_PROP_ASPECT_RATIO:
            if (value >= XINE_VO_ASPECT_NUM_RATIOS)
                value = XINE_VO_ASPECT_AUTO;
            this->aspect = value;
            return value;
    }
    return this->passthrough->set_property(this->passthrough, property, value);
}

static void 
buffer_get_property_min_max (vo_driver_t *this_gen,
                     int property, int *min, int *max) 
{
    buffer_driver_t *this = (buffer_driver_t *)this_gen;
    printf("buffer_get_property_min_max\n");
    this->passthrough->get_property_min_max(this->passthrough, property, min, max);
}

static int
buffer_gui_data_exchange (vo_driver_t *this_gen,
                 int data_type, void *data) 
{
    buffer_driver_t *this = (buffer_driver_t *)this_gen;
    printf("buffer_gui_data_exchange\n");
    return this->passthrough->gui_data_exchange(this->passthrough, data_type, data);
}

static void
buffer_dispose(vo_driver_t *this_gen)
{
    PyGILState_STATE gstate;
    buffer_driver_t *this = (buffer_driver_t *)this_gen;

    printf("buffer_dispose\n");

    gstate = PyGILState_Ensure();
    if (this->callback)
       Py_DECREF(this->callback);
    Py_DECREF(this->passthrough_pyobject);
    PyGILState_Release(gstate);

    this->yuv2rgb_factory->dispose(this->yuv2rgb_factory);
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
    if (passthrough && !Xine_VO_Driver_PyObject_Check(passthrough)) {
        PyErr_Format(xine_error, "Passthrough must be a VODriver object");
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
    this->vo_driver.overlay_blend           = _overlay_blend;
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
    this->passthrough = ((Xine_VO_Driver_PyObject *)passthrough)->driver;
    Py_INCREF(passthrough);
    this->passthrough_pyobject = passthrough;

    this->yuv2rgb_factory = yuv2rgb_factory_init(MODE_32_RGB, 0, NULL);

//    memcpy(&this->vo_driver, this->passthrough->driver, sizeof(vo_driver_t));
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


// These rle blend functions taken from xine (src/video_out/alphablend.c)

#define BLEND_BYTE(dst, src, o) (((src)*o + ((dst)*(0xf-o)))/0xf)

static void mem_blend32(uint8_t *mem, uint8_t *src, uint8_t o, int len) {
  uint8_t *limit = mem + len*4;
  while (mem < limit) {
    *mem = BLEND_BYTE(*mem, src[0], o);
    mem++;
    *mem = BLEND_BYTE(*mem, src[1], o);
    mem++;
    *mem = BLEND_BYTE(*mem, src[2], o);
    mem++;
    *mem = BLEND_BYTE(*mem, src[3], o);
    mem++;
  }
}


typedef struct {         /* CLUT == Color LookUp Table */
  uint8_t cb    : 8;
  uint8_t cr    : 8;
  uint8_t y     : 8;
  uint8_t foo   : 8;
} __attribute__ ((packed)) clut_t;


static void _overlay_mem_blend_8(uint8_t *mem, uint8_t val, uint8_t o, size_t sz)
{
   uint8_t *limit = mem + sz;
   while (mem < limit) {
      *mem = BLEND_BYTE(*mem, val, o);
      mem++;
   }
}

static void _overlay_blend_yuv(uint8_t *dst_base[3], vo_overlay_t * img_overl, int dst_width, int dst_height, int dst_pitches[3])
{
   clut_t *my_clut;
   uint8_t *my_trans;
   int src_width;
   int src_height;
   rle_elem_t *rle;
   rle_elem_t *rle_limit;
   int x_off;
   int y_off;
   int ymask, xmask;
   int rle_this_bite;
   int rle_remainder;
   int rlelen;
   int x, y;
   int clip_right;
   uint8_t clr = 0;

   src_width = img_overl->width;
   src_height = img_overl->height;
   rle = img_overl->rle;
   rle_limit = rle + img_overl->num_rle;
   x_off = img_overl->x;
   y_off = img_overl->y;

   if (!rle) return;

   //printf("_overlay_blend_yuv: rle=%x w=%d h=%d x=%d y=%d\n", rle, src_width, src_height, x_off, y_off);
   uint8_t *dst_y = dst_base[0] + dst_pitches[0] * y_off + x_off;
   uint8_t *dst_cr = dst_base[2] + (y_off / 2) * dst_pitches[1] + (x_off / 2) + 1;
   uint8_t *dst_cb = dst_base[1] + (y_off / 2) * dst_pitches[2] + (x_off / 2) + 1;
   my_clut = (clut_t *) img_overl->clip_color;
   my_trans = img_overl->clip_trans;

   /* avoid wraping overlay if drawing to small image */
   if( (x_off + img_overl->clip_right) < dst_width )
     clip_right = img_overl->clip_right;
   else
     clip_right = dst_width - 1 - x_off;

   /* avoid buffer overflow */
   if( (src_height + y_off) >= dst_height )
     src_height = dst_height - 1 - y_off;

   rlelen=rle_remainder=0;
   for (y = 0; y < src_height; y++) {
      ymask = ((img_overl->clip_top > y) || (img_overl->clip_bottom < y));
      xmask = 0;

      for (x = 0; x < src_width;) {
     uint16_t o;

     if (rlelen == 0) {
        rle_remainder = rlelen = rle->len;
        clr = rle->color;
        rle++;
     }
     if (rle_remainder == 0) {
        rle_remainder = rlelen;
     }
     if ((rle_remainder + x) > src_width) {
        /* Do something for long rlelengths */
        rle_remainder = src_width - x;
     }

     if (ymask == 0) {
        if (x <= img_overl->clip_left) {
           /* Starts outside clip area */
           if ((x + rle_remainder - 1) > img_overl->clip_left ) {
          /* Cutting needed, starts outside, ends inside */
          rle_this_bite = (img_overl->clip_left - x + 1);
          rle_remainder -= rle_this_bite;
          rlelen -= rle_this_bite;
          my_clut = (clut_t *) img_overl->color;
          my_trans = img_overl->trans;
          xmask = 0;
           } else {
          /* no cutting needed, starts outside, ends outside */
          rle_this_bite = rle_remainder;
          rle_remainder = 0;
          rlelen -= rle_this_bite;
          my_clut = (clut_t *) img_overl->color;
          my_trans = img_overl->trans;
          xmask = 0;
           }
        } else if (x < clip_right) {
           /* Starts inside clip area */
           if ((x + rle_remainder) > clip_right ) {
          /* Cutting needed, starts inside, ends outside */
          rle_this_bite = (clip_right - x);
          rle_remainder -= rle_this_bite;
          rlelen -= rle_this_bite;
          my_clut = (clut_t *) img_overl->clip_color;
          my_trans = img_overl->clip_trans;
          xmask++;
           } else {
          /* no cutting needed, starts inside, ends inside */
          rle_this_bite = rle_remainder;
          rle_remainder = 0;
          rlelen -= rle_this_bite;
          my_clut = (clut_t *) img_overl->clip_color;
          my_trans = img_overl->clip_trans;
          xmask++;
           }
        } else if (x >= clip_right) {
           /* Starts outside clip area, ends outsite clip area */
           if ((x + rle_remainder ) > src_width ) {
          /* Cutting needed, starts outside, ends at right edge */
          /* It should never reach here due to the earlier test of src_width */
          rle_this_bite = (src_width - x );
          rle_remainder -= rle_this_bite;
          rlelen -= rle_this_bite;
          my_clut = (clut_t *) img_overl->color;
          my_trans = img_overl->trans;
          xmask = 0;
           } else {
          /* no cutting needed, starts outside, ends outside */
          rle_this_bite = rle_remainder;
          rle_remainder = 0;
          rlelen -= rle_this_bite;
          my_clut = (clut_t *) img_overl->color;
          my_trans = img_overl->trans;
          xmask = 0;
           }
        }
     } else {
        /* Outside clip are due to y */
        /* no cutting needed, starts outside, ends outside */
        rle_this_bite = rle_remainder;
        rle_remainder = 0;
        rlelen -= rle_this_bite;
        my_clut = (clut_t *) img_overl->color;
        my_trans = img_overl->trans;
        xmask = 0;
     }
     o   = my_trans[clr];
     if (o) {
        if(o >= 15) {
           memset(dst_y + x, my_clut[clr].y, rle_this_bite);
           if (y & 1) {
          memset(dst_cr + (x >> 1), my_clut[clr].cr, (rle_this_bite+1) >> 1);
          memset(dst_cb + (x >> 1), my_clut[clr].cb, (rle_this_bite+1) >> 1);
           }
        } else {
           _overlay_mem_blend_8(dst_y + x, my_clut[clr].y, o, rle_this_bite);
           if (y & 1) {
          /* Blending cr and cb should use a different function, with pre -128 to each sample */
          _overlay_mem_blend_8(dst_cr + (x >> 1), my_clut[clr].cr, o, (rle_this_bite+1) >> 1);
          _overlay_mem_blend_8(dst_cb + (x >> 1), my_clut[clr].cb, o, (rle_this_bite+1) >> 1);
           }
        }

     }
     x += rle_this_bite;
     if (rle >= rle_limit) {
        break;
     }
      }
      if (rle >= rle_limit) {
     break;
      }

      dst_y += dst_pitches[0];

      if (y & 1) {
     dst_cr += dst_pitches[2];
     dst_cb += dst_pitches[1];
      }
   }
}


void _overlay_blend_yuy2 (uint8_t * dst_img, vo_overlay_t * img_overl,
                 int dst_width, int dst_height, int dst_pitch)
{
  clut_t *my_clut;
  uint8_t *my_trans;

  int src_width = img_overl->width;
  int src_height = img_overl->height;
  rle_elem_t *rle = img_overl->rle;
  rle_elem_t *rle_limit = rle + img_overl->num_rle;
  int x_off = img_overl->x;
  int y_off = img_overl->y;
  int x_odd = x_off & 1;
  int ymask;
  int rle_this_bite;
  int rle_remainder;
  int rlelen;
  int x, y;
  int l = 0;
  int clip_right;

  union {
    uint32_t value;
    uint8_t  b[4];
    uint16_t h[2];
  } yuy2;

  uint8_t clr = 0;

  int any_line_buffered = 0;
  uint8_t *(*blend_yuy2_data)[ 3 ] = 0;
  
  uint8_t *dst_y = dst_img + dst_pitch * y_off + 2 * x_off;
  uint8_t *dst;

  my_clut = (clut_t*) img_overl->clip_color;
  my_trans = img_overl->clip_trans;

  /* avoid wraping overlay if drawing to small image */
  if( (x_off + img_overl->clip_right) <= dst_width )
    clip_right = img_overl->clip_right;
  else
    clip_right = dst_width - x_off;

  /* avoid buffer overflow */
  if( (src_height + y_off) > dst_height )
    src_height = dst_height - y_off;

  if (src_height <= 0)
    return;

  rlelen=rle_remainder=0;
  for (y = 0; y < src_height; y++) {
    if (rle >= rle_limit)
      break;
    
    ymask = ((y < img_overl->clip_top) || (y >= img_overl->clip_bottom));

    dst = dst_y;
    for (x = 0; x < src_width;) {
      uint16_t o;

      if (rle >= rle_limit)
        break;
    
      if ((rlelen < 0) || (rle_remainder < 0)) {
      } 
      if (rlelen == 0) {
        rle_remainder = rlelen = rle->len;
        clr = rle->color;
        rle++;
      }
      if (rle_remainder == 0) {
        rle_remainder = rlelen;
      }
      if ((rle_remainder + x) > src_width) {
        /* Do something for long rlelengths */
        rle_remainder = src_width - x;
      }

      if (ymask == 0) {
        if (x < img_overl->clip_left) { 
          /* Starts outside clip area */
          if ((x + rle_remainder) > img_overl->clip_left ) {
            /* Cutting needed, starts outside, ends inside */
            rle_this_bite = (img_overl->clip_left - x);
            rle_remainder -= rle_this_bite;
            rlelen -= rle_this_bite;
            my_clut = (clut_t*) img_overl->color;
            my_trans = img_overl->trans;
          } else {
          /* no cutting needed, starts outside, ends outside */
            rle_this_bite = rle_remainder;
            rle_remainder = 0;
            rlelen -= rle_this_bite;
            my_clut = (clut_t*) img_overl->color;
            my_trans = img_overl->trans;
          }
        } else if (x < clip_right) {
          /* Starts inside clip area */
          if ((x + rle_remainder) > clip_right ) {
            /* Cutting needed, starts inside, ends outside */
            rle_this_bite = (clip_right - x);
            rle_remainder -= rle_this_bite;
            rlelen -= rle_this_bite;
            my_clut = (clut_t*) img_overl->clip_color;
            my_trans = img_overl->clip_trans;
          } else {
          /* no cutting needed, starts inside, ends inside */
            rle_this_bite = rle_remainder;
            rle_remainder = 0;
            rlelen -= rle_this_bite;
            my_clut = (clut_t*) img_overl->clip_color;
            my_trans = img_overl->clip_trans;
          }
        } else if (x >= clip_right) {
          /* Starts outside clip area, ends outsite clip area */
          if ((x + rle_remainder ) > src_width ) { 
            /* Cutting needed, starts outside, ends at right edge */
            /* It should never reach here due to the earlier test of src_width */
            rle_this_bite = (src_width - x );
            rle_remainder -= rle_this_bite;
            rlelen -= rle_this_bite;
            my_clut = (clut_t*) img_overl->color;
            my_trans = img_overl->trans;
          } else {
          /* no cutting needed, starts outside, ends outside */
            rle_this_bite = rle_remainder;
            rle_remainder = 0;
            rlelen -= rle_this_bite;
            my_clut = (clut_t*) img_overl->color;
            my_trans = img_overl->trans;
          }
        }
      } else {
        /* Outside clip are due to y */
        /* no cutting needed, starts outside, ends outside */
        rle_this_bite = rle_remainder;
        rle_remainder = 0;
        rlelen -= rle_this_bite;
        my_clut = (clut_t*) img_overl->color;
        my_trans = img_overl->trans;
      }
      o   = my_trans[clr];

      if (x < (dst_width - x_off)) {
        /* clip against right edge of destination area */
        if ((x + rle_this_bite) > (dst_width - x_off)) {
          int toClip = (x + rle_this_bite) - (dst_width - x_off);
          
          rle_this_bite -= toClip;
          rle_remainder += toClip;
          rlelen += toClip;
        }

        if (o) {
            l = rle_this_bite>>1;
            if( !((x_odd+x) & 1) ) {
              yuy2.b[0] = my_clut[clr].y;
              yuy2.b[1] = my_clut[clr].cb;
              yuy2.b[2] = my_clut[clr].y;
              yuy2.b[3] = my_clut[clr].cr;
            } else {
              yuy2.b[0] = my_clut[clr].y;
              yuy2.b[1] = my_clut[clr].cr;
              yuy2.b[2] = my_clut[clr].y;
              yuy2.b[3] = my_clut[clr].cb;
            }

          if (o >= 15) {
              while(l--) {
                *(uint16_t *)dst = yuy2.h[0];
                dst += 2;
                *(uint16_t *)dst = yuy2.h[1];
                dst += 2;
              }
              if(rle_this_bite & 1) {
                *(uint16_t *)dst = yuy2.h[0];
                dst += 2;
              }
          } else {
              if( l ) {
                mem_blend32(dst, &yuy2.b[0], o, l);
                dst += 4*l;
              }
              
              if(rle_this_bite & 1) {
                *dst = BLEND_BYTE(*dst, yuy2.b[0], o);
                dst++;
                *dst = BLEND_BYTE(*dst, yuy2.b[1], o);
                dst++;
              }
          }

        } else {
          dst += rle_this_bite*2;
        }
      }
      
      x += rle_this_bite;
    }
    
    dst_y += dst_pitch;
  }
}


static void
_overlay_blend(vo_driver_t *this_gen, vo_frame_t *frame_gen, vo_overlay_t *vo_overlay)
{
    buffer_driver_t *this = (buffer_driver_t *)this_gen;
    buffer_frame_t *frame = (buffer_frame_t *)frame_gen;

    //printf("buffer_overlay_blend: format=%d overlay=%x\n", frame->format, vo_overlay);
    if (frame->format == XINE_IMGFMT_YV12)
       _overlay_blend_yuv(frame->vo_frame.base, vo_overlay,
                      frame->width, frame->height,
                      frame->vo_frame.pitches);
    else
       _overlay_blend_yuy2(frame->vo_frame.base[0], vo_overlay,
                      frame->width, frame->height,
                      frame->vo_frame.pitches[0]);
}

static vo_info_t buffer_vo_info = {
    1,
    XINE_VISUAL_TYPE_NONE
};

plugin_info_t xine_vo_buffer_plugin_info[] = {
    { PLUGIN_VIDEO_OUT, 20, "buffer", XINE_VERSION_CODE, &buffer_vo_info, &buffer_init_class },
    { PLUGIN_NONE, 0, "", 0, NULL, NULL }
};


