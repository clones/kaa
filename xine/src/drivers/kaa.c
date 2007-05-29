
#include "kaa.h"
#include "video_out_kaa.h"
#include <sys/shm.h>
#include <sys/ipc.h>
#include <malloc.h>
#include "../config.h"

#if defined(ARCH_X86) || defined(ARCH_X86_64)
    #define YUY2_SIZE_THRESHOLD   400*280
#else
    #define YUY2_SIZE_THRESHOLD   2000*2000
#endif

#define NUM_FRAME_BUFFERS 3

typedef struct _kaa_vo_user_data {
    driver_info_common common;

    driver_info_common *passthrough_driver_info;

    // OSD
    PyObject *osd_configure_cb,
             *passthrough_pyobject;
    void *passthrough_visual;

    int yv12_width, yv12_height;
    uint8_t *yv12_planes[3];
    int yv12_strides[3];

    // Frame notification
    //yuv2rgb_factory_t *yuv2rgb_factory;
    uint8_t *shmem, *buffers[NUM_FRAME_BUFFERS];
    int do_notify_frame, notify_fd, shm_id, cur_buffer_idx, buffer_size;

    // Not used right now.
    int notify_frame_width, notify_frame_height;

} kaa_vo_user_data;

typedef struct _kaa_frame_user_data {
    //yuv2rgb_t *yuv2rgb;
} kaa_frame_user_data;


typedef struct {
    uint8_t lock;
    uint16_t width, height, stride;
    double aspect;
} buffer_header_t;

typedef struct {
    uint32_t shm_id;
    uint32_t offset;
    char padding[8];
} notify_packet_t;


#if 0

static void
_alloc_yv12(kaa_vo_user_data *user_data, int width, int height)
{
    int i;

    user_data->yv12_strides[0] = 8*((width + 7) / 8);
    user_data->yv12_strides[1] = 8*((width + 15) / 16);
    user_data->yv12_strides[2] = 8*((width + 15) / 16);

    for (i = 0; i < 3; i++) {
        if (user_data->yv12_planes[i])
            free(user_data->yv12_planes[i]);

        user_data->yv12_planes[i] = (uint8_t *)memalign(16, user_data->yv12_strides[i] * (height >> (i > 0)));
    }
    user_data->yv12_width = width;
    user_data->yv12_height = height;
}


static void
_kaa_frame_to_buffer(kaa_vo_user_data *user_data, vo_frame_t *frame, kaa_frame_user_data *frame_user_data, 
                     int dst_width, int dst_height)
{
    int y_stride = frame->pitches[0],
        uv_stride = frame->pitches[1];
    if (dst_width <= 0 || dst_height <= 0)
        return;

    // TODO: use swscaler when it's available.

    if (frame->format == XINE_IMGFMT_YUY2 && dst_width*dst_height > YUY2_SIZE_THRESHOLD) {
        y_stride = 8*((frame->width + 7) / 8);
        uv_stride = 8*((frame->width + 15) / 16);
    }

    if (frame->width != frame_user_data->yuv2rgb->source_width ||
        frame->height != frame_user_data->yuv2rgb->source_height ||
        (frame->format == XINE_IMGFMT_YV12 && (
             y_stride != frame_user_data->yuv2rgb->y_stride ||
             uv_stride != frame_user_data->yuv2rgb->uv_stride)
        ) ||
        (frame->format == XINE_IMGFMT_YUY2 &&
             y_stride != frame_user_data->yuv2rgb->y_stride
        ) ||
        dst_width != frame_user_data->yuv2rgb->dest_width ||
        dst_height != frame_user_data->yuv2rgb->dest_height) {

        frame_user_data->yuv2rgb->configure(frame_user_data->yuv2rgb, frame->width, frame->height,
            y_stride, uv_stride, dst_width, dst_height, 4*dst_width);

    }

    if (frame->format == XINE_IMGFMT_YV12) {
        frame_user_data->yuv2rgb->yuv2rgb_fun(frame_user_data->yuv2rgb,
                user_data->frame_buffer + 16, frame->base[0], frame->base[1], frame->base[2]);
    } else {
        if (dst_width * dst_height > YUY2_SIZE_THRESHOLD) {
            // Naive optimization: yuv2rgb has an accelerated version
            // but yuy22rgb doesn't.  So when the area of the image is
            // greater than the size threshold (determined empirically)
            // first convert the yuy2 image to yv12 and then convert
            // yv12 to rgb, both operations of which are accelerated.
            if (user_data->yv12_width != frame->width || user_data->yv12_height != frame->height)
                _alloc_yv12(user_data, frame->width, frame->height);

            yuy2_to_yv12(frame->base[0], frame->pitches[0],
                         user_data->yv12_planes[0], user_data->yv12_strides[0],
                         user_data->yv12_planes[1], user_data->yv12_strides[1],
                         user_data->yv12_planes[2], user_data->yv12_strides[2],
                         frame->width, frame->height);
            frame_user_data->yuv2rgb->yuv2rgb_fun (frame_user_data->yuv2rgb, user_data->frame_buffer + 16,
                                         user_data->yv12_planes[0],
                                         user_data->yv12_planes[1],
                                         user_data->yv12_planes[2]);
        } else {
            frame_user_data->yuv2rgb->yuy22rgb_fun(frame_user_data->yuv2rgb, user_data->frame_buffer + 16,
                                            frame->base[0]);
        }
    }
}
#endif 

static int
setup_shmem(kaa_vo_user_data *user_data, int stride, int height)
{   
    int i;

    if (user_data->shm_id) {
        struct shmid_ds shmemds; 
        shmctl(user_data->shm_id, IPC_RMID, &shmemds);
        shmdt(user_data->shmem);
    }
    user_data->buffer_size = 32 + stride*height*2;
    user_data->shm_id = shmget(IPC_PRIVATE, user_data->buffer_size * NUM_FRAME_BUFFERS, IPC_CREAT | 0600);
    if (user_data->shm_id == -1) 
        // TODO: get this error back into python space
        return -1;

    user_data->shmem = shmat(user_data->shm_id, NULL, 0);
    for (i = 0; i < NUM_FRAME_BUFFERS; i++) {
        user_data->buffers[i] = user_data->shmem + user_data->buffer_size * i;
        *user_data->buffers[i] = 0;
    }
    user_data->cur_buffer_idx = 0;
    //printf("[buffer] h=%d stride=%d shmid=%d\n", height, stride, user_data->shm_id);
    return 0;
}

static inline int
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
    return *lock == 0;
} 


static long long 
get_usecs(void)
{
    struct timeval tv;
    gettimeofday(&tv, NULL);
    return (long long)((tv.tv_sec * 1000000.0) + tv.tv_usec);
}

static int
handle_frame_cb(int cmd, vo_frame_t *frame, void **frame_user_data_gen, void *data)
{
    kaa_vo_user_data *user_data = (kaa_vo_user_data *)data;
    //kaa_frame_user_data *frame_user_data = *(kaa_frame_user_data **)frame_user_data_gen;

    if (cmd == KAA_VO_HANDLE_FRAME_DISPLAY_PRE_OSD && user_data->do_notify_frame) {
        uint8_t *lock, *y_dst, *u_dst, *v_dst;
        int last_idx = user_data->cur_buffer_idx > 0 ? user_data->cur_buffer_idx - 1 : NUM_FRAME_BUFFERS - 1,
            stride = (frame->format == XINE_IMGFMT_YUY2) ? frame->pitches[0] >> 1: frame->pitches[0];

        if (32 + stride*frame->height*2 > user_data->buffer_size)
            setup_shmem(user_data, stride, frame->height);

        notify_packet_t notify = {
            .shm_id = user_data->shm_id,
            .offset = user_data->buffers[user_data->cur_buffer_idx] - user_data->buffers[0]
        };

        buffer_header_t header = {
            .lock = 0,
            .width = frame->width,
            .height = frame->height,
            .stride = stride,
            .aspect = frame->ratio
        };

        lock = user_data->buffers[user_data->cur_buffer_idx];
        y_dst = lock + 32;
        u_dst = y_dst + (stride * frame->height);
        v_dst = u_dst + (stride * frame->height >> 2);

        // Wait for the last buffer to be unlocked (i.e. has been rendered) 
        // before delivering the next one.
        if (*user_data->buffers[last_idx] && !wait_for_buffer(user_data->buffers[last_idx], 0.1))
            // Buffer locked too long.
            return 0;


        if (frame->format == XINE_IMGFMT_YV12) {
            //long long t0=get_usecs();
            yv12_to_yv12(frame->base[0], frame->pitches[0], y_dst, frame->pitches[0],
                         frame->base[1], frame->pitches[1], u_dst, frame->pitches[1],
                         frame->base[2], frame->pitches[2], v_dst, frame->pitches[2],
                         frame->width, frame->height);
             //printf("YV12 Convert: %d\n", get_usecs()-t0);
        } else if (frame->format == XINE_IMGFMT_YUY2 ) {
            //long long t0=get_usecs();
            yuy2_to_yv12(frame->base[0], frame->pitches[0], 
                         y_dst, stride, u_dst, stride >> 1, v_dst, stride >> 1,
                         frame->width, frame->height);
            //printf("YUY2 Convert: %d\n", get_usecs()-t0);
        } else {
            printf("Unknown frame format!\n");
            return 0;
        }

        memcpy(user_data->buffers[user_data->cur_buffer_idx], &header, sizeof(header));
        *lock = 1;
        write(user_data->notify_fd, &notify, sizeof(notify));
        fsync(user_data->notify_fd);
        user_data->cur_buffer_idx++;
        if (user_data->cur_buffer_idx == NUM_FRAME_BUFFERS)
            user_data->cur_buffer_idx = 0;
    }

#if 0
    switch (cmd) {
        case KAA_VO_HANDLE_FRAME_DISPLAY_PRE_OSD:
        {
        case KAA_VO_HANDLE_FRAME_ALLOC:
            *frame_user_data_gen = malloc(sizeof(kaa_frame_user_data));
            frame_user_data = *(kaa_frame_user_data **)frame_user_data_gen;
            memset(frame_user_data, 0, sizeof(kaa_frame_user_data));
            frame_user_data->yuv2rgb = user_data->yuv2rgb_factory->create_converter(user_data->yuv2rgb_factory);
            break;


        case KAA_VO_HANDLE_FRAME_DISPOSE:
            frame_user_data->yuv2rgb->dispose(frame_user_data->yuv2rgb);
            free(*frame_user_data_gen);
            break;

        case KAA_VO_HANDLE_FRAME_DISPLAY_PRE_OSD: {
            struct { short lock, width, height; double aspect; } header = { .lock = 0x10 };
            struct timeval curtime;
            struct timezone tz;
            double start_time, now;
            int dst_width = user_data->notify_frame_width, 
                dst_height = user_data->notify_frame_height;

            if (!user_data->frame_buffer || !user_data->do_notify_frame)
                break;

            // Wait at most 0.1 seconds for the client to unlock the buffer.
            gettimeofday(&curtime, &tz);
            start_time = now = curtime.tv_sec + (curtime.tv_usec/(1000.0*1000));
            while (user_data->frame_buffer[0] == 0x20 && now - start_time < 0.1) {
                gettimeofday(&curtime, &tz);
                now = curtime.tv_sec + (curtime.tv_usec/(1000.0*1000));
                usleep(1);
            }
            if (now - start_time >= 0.1)
                break;
            
            if (dst_width == -1)
                dst_width = frame->width;
            if (dst_height == -1)
                dst_height = frame->height;

            _kaa_frame_to_buffer(user_data, frame, frame_user_data, dst_width, dst_height);

            header.width = dst_width;
            header.height = dst_height;
            header.aspect = frame->ratio;
            memcpy(user_data->frame_buffer, &header, sizeof(header));
            *user_data->frame_buffer = 0x20;

            // TODO: could callback into python to notify new frame.  (Note:
            // we're in a thread here, will require GIL.)
            break;
        }
    }
#endif
    return 0;
}

static void *
_get_ptr_from_pyobject(PyObject *o, int *buflen)
{
    void *data = 0;
    int len;

    if (PyNumber_Check(o)) {
        data = (void *) PyLong_AsLong(o);
        if (buflen)
            *buflen = -1;
    } else {
        if (PyObject_AsWriteBuffer(o, (void **) &data, &len) == -1)
            return NULL;
        if (buflen)
            *buflen = len;
    }
    return data;
}

void 
osd_configure_cb(int width, int height, double aspect, void *data, uint8_t **buffer_return, int *buffer_stride_return)
{
    kaa_vo_user_data *user_data = (kaa_vo_user_data *)data;
    PyObject *args, *result;
    PyGILState_STATE gstate;

    *buffer_return = 0;
    *buffer_stride_return = 0;

    if (!user_data || !user_data->osd_configure_cb || !Py_IsInitialized())
        return;

    gstate = PyGILState_Ensure();

    args = Py_BuildValue("(iid)", width, height, aspect);
    result = PyEval_CallObject(user_data->osd_configure_cb, args);
    if (result) {
        PyObject *py_osd_buffer, *py_frame_buffer = 0;
        int buflen = -1;

        if (!PyArg_ParseTuple(result, "Oi|O", &py_osd_buffer, buffer_stride_return, &py_frame_buffer))
            goto bail;

        if ((*buffer_return = _get_ptr_from_pyobject(py_osd_buffer, &buflen)) == 0)
            goto bail;
        if (buflen != -1 && buflen < width * height * 4) {
            PyErr_Format(PyExc_ValueError, "OSD buffer is not big enough");
            goto bail;
        }
/*
        if (py_frame_buffer && (frame_buffer = _get_ptr_from_pyobject(py_frame_buffer, &buflen)))
            user_data->frame_buffer = frame_buffer;
        if (buflen != -1 && buflen < width * height * 4) {
            PyErr_Format(PyExc_ValueError, "Frame buffer is not big enough");
            goto bail;
        }
*/
    }

bail:
    if (result) {
        Py_DECREF(result);
    }

    if (PyErr_Occurred()) {
        printf("Exception in osd_configure_cb callback:\n");
        PyErr_Print();
    }
    Py_DECREF(args);
    PyGILState_Release(gstate);
}


PyObject *
_control(PyObject *self, PyObject *args, PyObject *kwargs)
{
    kaa_vo_user_data *user_data = (kaa_vo_user_data *)PyCObject_AsVoidPtr(self);
    PyObject *cmd_arg = NULL, *retval = NULL;
    kaa_driver_t *driver = (kaa_driver_t *)user_data->common.driver;
    char *command;

    if (!PyArg_ParseTuple(args, "s|O", &command, &cmd_arg))
        return NULL;

    #define type_check(var, tp, errmsg) \
        if (!var || !Py ## tp ## _Check(var)) { PyErr_Format(xine_error, errmsg); return NULL;}
    #define gui_send(cmd, val) \
        driver->vo_driver.gui_data_exchange(&driver->vo_driver, GUI_SEND_KAA_VO_ ## cmd, (void *)val);

    if (!strcmp(command, "set_notify_frame")) {
        type_check(cmd_arg, Bool, "Argument must be a boolean");
        user_data->do_notify_frame = PyLong_AsLong(cmd_arg);
    }
    else if (!strcmp(command, "set_notify_frame_size")) {
        if (!PyArg_ParseTuple(cmd_arg, "ii", &user_data->notify_frame_width, &user_data->notify_frame_height))
            return NULL;
    }
    else if (!strcmp(command, "set_passthrough")) {
        type_check(cmd_arg, Bool, "Argument must be a boolean");
        gui_send(SET_PASSTHROUGH, PyLong_AsLong(cmd_arg));
    }
    else if (!strcmp(command, "set_osd_visibility")) {
        type_check(cmd_arg, Bool, "Argument must be a boolean");
        gui_send(OSD_SET_VISIBILITY, PyLong_AsLong(cmd_arg));
    }
    else if (!strcmp(command, "set_osd_alpha")) {
        type_check(cmd_arg, Number, "Argument must be an integer");
        gui_send(OSD_SET_ALPHA, PyLong_AsLong(cmd_arg));
    }
    else if (!strcmp(command, "osd_invalidate_rect")) {
        struct { int x, y, w, h; } *r;
        int nrects, i;
        type_check(cmd_arg, List, "Argument must be a List of 4-tuples");
        nrects = PySequence_Length(cmd_arg);
        r = malloc(sizeof(int)*4*(nrects+1));
        for (i = 0; i < nrects; i++) {
            PyObject *tuple = PyList_GetItem(cmd_arg, i);
            if (!PyArg_ParseTuple(tuple, "iiii", &r[i].x, &r[i].y, &r[i].w, &r[i].h))
                return NULL;
        }
        r[i].w = 0; // sentinel
        gui_send(OSD_INVALIDATE_RECT, r);
        free(r);
    }
    /*
    else if (!strcmp(command, "set_osd_slice")) {
        struct { int y, h; } slice;
        if (!PyArg_ParseTuple(cmd_arg, "ii", &slice.y, &slice.h))
            return NULL;
        gui_send(OSD_SET_SLICE, &slice);
    }
    */
    else {
        PyErr_Format(PyExc_ValueError, "Invalid control '%s'", command);
        return NULL;
    }

    if (retval == NULL) {
        retval = Py_None;
        Py_INCREF(retval);
    }
    return retval;
}


PyMethodDef control_def = {
    "control", (PyCFunction)_control, METH_VARARGS | METH_KEYWORDS, NULL
};


void
kaa_driver_dealloc(void *data)
{
    PyGILState_STATE gstate;
    kaa_vo_user_data *user_data = (kaa_vo_user_data *)data;
    int i;
 
    gstate = PyGILState_Ensure();

    if (user_data->osd_configure_cb) {
        Py_DECREF(user_data->osd_configure_cb);
    }
    if (user_data->passthrough_pyobject) {
        Py_DECREF(user_data->passthrough_pyobject);
    }
    PyGILState_Release(gstate);

    if (user_data->passthrough_driver_info && user_data->passthrough_driver_info->dealloc_cb)
        user_data->passthrough_driver_info->dealloc_cb(user_data->passthrough_driver_info);
    if (user_data->passthrough_visual)
        free(user_data->passthrough_visual);

    //user_data->yuv2rgb_factory->dispose(user_data->yuv2rgb_factory);
     for (i = 0; i < 3; i++) {
         if (user_data->yv12_planes[i])
             free(user_data->yv12_planes[i]);
     }

    if (user_data->shm_id) {
        struct shmid_ds shmemds; 
        shmctl(user_data->shm_id, IPC_RMID, &shmemds);
        shmdt(user_data->shmem);
    }

    free(user_data);
}


int
kaa_get_visual_info(Xine_PyObject *xine, PyObject *kwargs, void **visual_return, 
                    driver_info_common **driver_info_return)
{
    kaa_visual_t vis;
    vo_driver_t *passthrough_driver;
    kaa_vo_user_data *user_data;
    PyObject *o, *passthrough = NULL, *control_return = NULL, *osd_configure_cb_pyobject = NULL;
    void *passthrough_visual;
    driver_info_common *passthrough_driver_info;
    int passthrough_visual_type, notify_fd = -1;

    passthrough = PyDict_GetItemString(kwargs, "passthrough");
    if (!passthrough || !PyString_Check(passthrough)) {
        PyErr_Format(xine_error, "Passthrough must be a string");
        return 0;
    }

    if (!driver_get_visual_info(xine, PyString_AsString(passthrough), kwargs, &passthrough_visual_type, 
                                &passthrough_visual, &passthrough_driver_info))
        return 0;



    passthrough_driver = _x_load_video_output_plugin(xine->xine, PyString_AsString(passthrough), 
                                                     passthrough_visual_type, passthrough_visual);
    if (passthrough_driver_info)
        passthrough_driver_info->driver = passthrough_driver;

    if (!passthrough_driver) {
        PyErr_Format(xine_error, "Failed to initialize passthrough driver: %s", PyString_AsString(passthrough));
        return 0;
    }

    memset(&vis, 0, sizeof(vis));
    vis.passthrough_driver      = PyString_AsString(passthrough);
    vis.passthrough_visual_type = passthrough_visual_type;
    vis.passthrough_visual      = passthrough_visual;
    vis.passthrough             = passthrough_driver;
    vis.handle_frame_cb         = handle_frame_cb;

    if (PyMapping_HasKeyString(kwargs, "vsync")) {
        if (PyObject_IsTrue(PyDict_GetItemString(kwargs, "vsync")) && 
            passthrough_visual_type == XINE_VISUAL_TYPE_X11)
            vis.use_opengl_vsync = 1;
    }

    if (PyMapping_HasKeyString(kwargs, "osd_configure_cb")) {
        vis.osd_configure_cb = osd_configure_cb;
        o = PyDict_GetItemString(kwargs, "osd_configure_cb");
        if (!PyCallable_Check(o)) {
            PyErr_Format(PyExc_ValueError, "osd_configure_cb must be callable");
            return 0;
        }
        osd_configure_cb_pyobject = o;
        Py_INCREF(o);
    }

    if (PyMapping_HasKeyString(kwargs, "notify_fd")) {
        o = PyDict_GetItemString(kwargs, "notify_fd");
        if (!PyNumber_Check(o)) {
            PyErr_Format(PyExc_ValueError, "notify_fd must be an integer (file descriptor)");
            return 0;
        }
        notify_fd = PyLong_AsLong(o);
    }

    Py_INCREF(passthrough);

    user_data = malloc(sizeof(kaa_vo_user_data));
    memset(user_data, 0, sizeof(kaa_vo_user_data));
    user_data->passthrough_pyobject    = passthrough;
    user_data->osd_configure_cb        = osd_configure_cb_pyobject;
    user_data->common.dealloc_cb       = kaa_driver_dealloc;
    user_data->passthrough_visual      = passthrough_visual;
    user_data->passthrough_driver_info = passthrough_driver_info;
    user_data->notify_frame_width      = -1;
    user_data->notify_frame_height     = -1;
    user_data->do_notify_frame         = 0;
    user_data->notify_fd               = notify_fd;
    //user_data->yuv2rgb_factory         = yuv2rgb_factory_init(MODE_32_RGB, 0, NULL);

    vis.osd_configure_cb_data = user_data;
    vis.handle_frame_cb_data  = user_data;

    control_return = PyDict_GetItemString(kwargs, "control_return");
    if (control_return && PyList_Check(control_return)) {
        PyObject *py_ud = PyCObject_FromVoidPtr((void *)user_data, NULL);
        PyObject *control = PyCFunction_New(&control_def, py_ud);
        PyList_Append(control_return, control);
        Py_DECREF(control);
        Py_DECREF(py_ud);
    }

    *visual_return = malloc(sizeof(vis));
    memcpy(*visual_return, &vis, sizeof(vis));
    *driver_info_return = (driver_info_common *)user_data;
    return 1;
}

