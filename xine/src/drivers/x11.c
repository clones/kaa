#include "x11.h"

PyTypeObject *X11Window_PyObject_Type;
int (*x11window_object_decompose)(PyObject *, Window *, Display **);

typedef struct _x11_callback_user_data {
    PyObject *frame_output_callback, 
             *dest_size_callback;
    Display *display;
} x11_callback_user_data;


typedef struct _x11_driver_finalize_data {
    x11_callback_user_data *user_data;
} x11_driver_finalize_data;

static void x11_frame_output_cb(void *data, int video_width, int video_height,
                double video_pixel_aspect, int *dest_x, int *dest_y,
                int *dest_width, int *dest_height,
                double *dest_pixel_aspect, int *win_x, int *win_y) 
{
    x11_callback_user_data *user_data = (x11_callback_user_data *)data;
    PyObject *args, *result;
    PyGILState_STATE gstate;
    int success = 0;

    if (!user_data->frame_output_callback) {
        // This should never happen because it's checked in x11_open_video_driver()
        printf("OOPS!  No frame output callback specified.\n");
        return;
    }


    gstate = PyGILState_Ensure();
    args = Py_BuildValue("(iid)", video_width, video_height, video_pixel_aspect);
    result = PyEval_CallObject(user_data->frame_output_callback, args);
    Py_DECREF(args);
    if (result) {
        if (PyBool_Check(result)) {
            // Probably WeakCallback returning False because we're on shutdown.
            success = 0;
        } else if (!PyArg_ParseTuple(result, "(ii)(ii)(ii)d", dest_x, dest_y, win_x, win_y,
                              dest_width, dest_height, dest_pixel_aspect)) {
            // FIXME: find a way to propagate this back to the main thread.
            printf("EXCEPTION: frame_output_cb returned bad arguments.\n");
            PyErr_Print();
        } else
            success = 1;

        Py_DECREF(result);
    } else {
        // FIXME: find a way to propagate this back to the main thread.
        printf("EXCEPTION in frame_output_cb!\n");
        PyErr_Print();
    }

    PyGILState_Release(gstate);

    if (!success) {
        // Call to python space failed, but we need to set some sane defaults
        // here, or else xine does ugly things.
        *dest_x = *dest_y = *win_x = *win_y = 0;
        *dest_width = *dest_height = 50;
        *dest_pixel_aspect = 1;
    }
}


xine_video_port_t *
x11_open_video_driver(Xine_PyObject *xine, char *driver, PyObject *kwargs, 
                      void **driver_data)
{
    x11_visual_t vis;
    xine_video_port_t *vo;
    x11_callback_user_data *user_data;
    x11_driver_finalize_data *finalize_data;
    PyObject *window, *frame_output_callback, *dest_size_callback;

    window = PyDict_GetItemString(kwargs, "window");
    if (!x11window_object_decompose(window, &vis.d, (Display **)&vis.display)) {
        PyErr_Format(xine_error, "Error in window parameter.");
        return NULL;
    }

    frame_output_callback = PyDict_GetItemString(kwargs, "frame_output_cb");
    dest_size_callback = PyDict_GetItemString(kwargs, "dest_size_cb");

    if (!frame_output_callback || !dest_size_callback) {
        PyErr_Format(xine_error, "Must specify frame_output_cb and dest_size_cb");
        return NULL;
    }

    user_data = malloc(sizeof(x11_callback_user_data));
    finalize_data = malloc(sizeof(x11_driver_finalize_data));

    user_data->frame_output_callback = frame_output_callback;
    user_data->dest_size_callback = dest_size_callback;
    user_data->display = vis.display;
    if (frame_output_callback)
        Py_INCREF(frame_output_callback);
    if (dest_size_callback)
        Py_INCREF(dest_size_callback);

    vis.screen = DefaultScreen(vis.display);
    vis.user_data = user_data;
    vis.frame_output_cb = x11_frame_output_cb;
//   vis.dest_size_cb = x11_dest_size_cb;

    vo = xine_open_video_driver(xine->xine, driver, XINE_VISUAL_TYPE_X11, (void *)&vis);

    finalize_data->user_data = user_data;
    *(x11_driver_finalize_data **)driver_data = finalize_data;      
    return vo;
}

void
x11_driver_dealloc(void *data)
{
    x11_callback_user_data *user_data = (x11_callback_user_data *)data;
    if (user_data->frame_output_callback)
        Py_DECREF(user_data->frame_output_callback);
    if (user_data->dest_size_callback)
        Py_DECREF(user_data->dest_size_callback);
    free(user_data);
}

void 
x11_open_video_driver_finalize(Xine_Video_Port_PyObject *vo, void *_finalize_data)
{
    x11_driver_finalize_data *finalize_data = (x11_driver_finalize_data *)_finalize_data;

    if (!finalize_data)
        return;

    vo->driver_dealloc_cb = x11_driver_dealloc;
    vo->driver_dealloc_data = finalize_data->user_data;
    free(finalize_data);
}

