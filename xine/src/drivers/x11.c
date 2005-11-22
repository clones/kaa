#include "x11.h"

PyTypeObject *X11Window_PyObject_Type;
int (*x11window_object_decompose)(PyObject *, Window *, Display **);

typedef struct _x11_vo_user_data {
    driver_info_common common;

    PyObject *frame_output_callback, 
             *dest_size_callback;
    Display *display;
    PyObject *window_pyobject;
} x11_vo_user_data;


static void x11_frame_output_cb(void *data, int video_width, int video_height,
                double video_pixel_aspect, int *dest_x, int *dest_y,
                int *dest_width, int *dest_height,
                double *dest_pixel_aspect, int *win_x, int *win_y) 
{
    x11_vo_user_data *user_data = (x11_vo_user_data *)data;
    PyObject *args, *result;
    PyGILState_STATE gstate;
    int success = 0;

    if (!user_data->frame_output_callback) {
        // This should never happen because it's checked in x11_open_video_driver()
        printf("OOPS!  No frame output callback specified.\n");
        return;
    }
    if (!Py_IsInitialized())
        return;

    gstate = PyGILState_Ensure();
    args = Py_BuildValue("(iid)", video_width, video_height, video_pixel_aspect);
    result = PyEval_CallObject(user_data->frame_output_callback, args);
    Py_DECREF(args);
    if (result) {
        if (PyBool_Check(result) || result == Py_None) {
            // Probably WeakCallback returning False because we're on shutdown.
            success = 0;
        } else if (!PyArg_ParseTuple(result, "(ii)(ii)(ii)d", dest_x, dest_y, win_x, win_y,
                              dest_width, dest_height, dest_pixel_aspect)) {
            // FIXME: find a way to propagate this back to the main thread.
            printf("EXCEPTION: frame_output_cb returned bad arguments (%s).\n", result->ob_type->tp_name);
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



static void x11_dest_size_cb(void *data, int video_width, int video_height,
                double video_pixel_aspect, int *dest_width, int *dest_height,
                double *dest_pixel_aspect) 
{
    x11_vo_user_data *user_data = (x11_vo_user_data *)data;
    PyObject *args, *result;
    PyGILState_STATE gstate;
    int success = 0;

    if (!user_data->dest_size_callback) {
        // This should never happen because it's checked in x11_open_video_driver()
        printf("OOPS!  No frame output callback specified.\n");
        return;
    }

    gstate = PyGILState_Ensure();
    args = Py_BuildValue("(iid)", video_width, video_height, video_pixel_aspect);
    result = PyEval_CallObject(user_data->dest_size_callback, args);
    Py_DECREF(args);
    if (result) {
        if (PyBool_Check(result) || result == Py_None) {
            // Probably WeakCallback returning False because we're on shutdown.
            success = 0;
        } else if (!PyArg_ParseTuple(result, "(ii)d", dest_width, dest_height, dest_pixel_aspect)) {
            // FIXME: find a way to propagate this back to the main thread.
            printf("EXCEPTION: dest_size_cb returned bad arguments (%s).\n", result->ob_type->tp_name);
            PyErr_Print();
        } else
            success = 1;

        Py_DECREF(result);
    } else {
        // FIXME: find a way to propagate this back to the main thread.
        printf("EXCEPTION in dest_size_cb!\n");
        PyErr_Print();
    }
    PyGILState_Release(gstate);

    if (!success) {
        // Call to python space failed, but we need to set some sane defaults
        // here, or else xine does ugly things.
        *dest_width = *dest_height = 50;
        *dest_pixel_aspect = 1;
    }
}

void
x11_driver_dealloc(void *data)
{
    PyGILState_STATE gstate;
    x11_vo_user_data *user_data = (x11_vo_user_data *)data;
    
    gstate = PyGILState_Ensure();
    if (user_data->frame_output_callback) {
        Py_DECREF(user_data->frame_output_callback);
    }
    if (user_data->dest_size_callback) {
        Py_DECREF(user_data->dest_size_callback);
    }
    Py_DECREF(user_data->window_pyobject);
    PyGILState_Release(gstate);
    free(user_data);
}


int
x11_get_visual_info(Xine_PyObject *xine, PyObject *kwargs, void **visual_return,
                    driver_info_common **driver_info_return)
{
    x11_visual_t vis;
    x11_vo_user_data *user_data;
    PyObject *window, *frame_output_callback, *dest_size_callback;

    window = PyDict_GetItemString(kwargs, "window");
    if (!x11window_object_decompose(window, &vis.d, (Display **)&vis.display)) {
        PyErr_Format(xine_error, "Error in window parameter.");
        return 0;
    }

    frame_output_callback = PyDict_GetItemString(kwargs, "frame_output_cb");
    dest_size_callback = PyDict_GetItemString(kwargs, "dest_size_cb");

    if (!frame_output_callback || !dest_size_callback) {
        PyErr_Format(xine_error, "Must specify frame_output_cb and dest_size_cb");
        return 0;
    }


    user_data = malloc(sizeof(x11_vo_user_data));
    user_data->frame_output_callback = frame_output_callback;
    user_data->dest_size_callback = dest_size_callback;
    user_data->display = vis.display;
    user_data->window_pyobject = window;
    user_data->common.dealloc_cb = x11_driver_dealloc;
    Py_INCREF(window);
    if (frame_output_callback)
        Py_INCREF(frame_output_callback);
    if (dest_size_callback)
        Py_INCREF(dest_size_callback);

    vis.screen = DefaultScreen(vis.display);
    vis.user_data = user_data;
    vis.frame_output_cb = x11_frame_output_cb;
    vis.dest_size_cb = x11_dest_size_cb;

    *visual_return = malloc(sizeof(vis));
    memcpy(*visual_return, &vis, sizeof(vis));
    *driver_info_return = (driver_info_common *)user_data;
    return 1;
}
