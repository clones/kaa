#include "kaa.h"
#include "video_out_kaa.h"

typedef struct _kaa_vo_user_data {
    driver_info_common common;
    PyObject *send_frame_cb, *osd_configure_cb,
             *passthrough_pyobject;
    void *passthrough_visual;
    driver_info_common *passthrough_driver_info;
} kaa_vo_user_data;


PyObject *
_unlock_frame_cb(PyObject *self, PyObject *args, PyObject *kwargs)
{
    pthread_mutex_t *lock = (pthread_mutex_t *)PyCObject_AsVoidPtr(self);
    pthread_mutex_unlock(lock);
    Py_INCREF(Py_None);
    return Py_None;
}

PyMethodDef unlock_frame_def = {
    "unlock_frame_cb", (PyCFunction)_unlock_frame_cb, METH_VARARGS, NULL
};


void send_frame_cb(int width, int height, double aspect, uint8_t *buffer, pthread_mutex_t *buffer_lock, void *data)
{
    kaa_vo_user_data *user_data = (kaa_vo_user_data *)data;
    PyObject *args, *result, *unlock_frame_cb, *lock_pyobject;
    PyGILState_STATE gstate;

    if (!user_data || !user_data->send_frame_cb || !Py_IsInitialized()) {
        pthread_mutex_unlock(buffer_lock);
        return;
    }

    gstate = PyGILState_Ensure();

    lock_pyobject = PyCObject_FromVoidPtr((void *)buffer_lock, NULL);
    unlock_frame_cb = PyCFunction_New(&unlock_frame_def, lock_pyobject);

    args = Py_BuildValue("(iidiO)", width, height, aspect, (long)buffer, unlock_frame_cb);
    Py_DECREF(unlock_frame_cb);
    Py_DECREF(lock_pyobject);
    result = PyEval_CallObject(user_data->send_frame_cb, args);
    if (result)
        Py_DECREF(result);
    else {
        printf("Exception in kaa_send_frame callback:\n");
        PyErr_Print();
    }
    Py_DECREF(args);
    PyGILState_Release(gstate);
}

void 
osd_configure_cb(int width, int height, double aspect, void *data)
{
    kaa_vo_user_data *user_data = (kaa_vo_user_data *)data;
    PyObject *args, *result;
    PyGILState_STATE gstate;

    if (!user_data || !user_data->osd_configure_cb || !Py_IsInitialized())
        return;

    gstate = PyGILState_Ensure();

    args = Py_BuildValue("(iid)", width, height, aspect);
    result = PyEval_CallObject(user_data->osd_configure_cb, args);
    if (result)
        Py_DECREF(result);
    else {
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

    if (!strcmp(command, "set_send_frame")) {
        type_check(cmd_arg, Bool, "Argument must be a boolean");
        gui_send(SET_SEND_FRAME, PyLong_AsLong(cmd_arg));
    }
    else if (!strcmp(command, "set_send_frame_size")) {
        struct { int w, h; } size;
        if (!PyArg_ParseTuple(cmd_arg, "ii", &size.w, &size.h))
            return NULL;
        gui_send(SET_SEND_FRAME_SIZE, &size);
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
 
    gstate = PyGILState_Ensure();
    if (user_data->send_frame_cb) {
        Py_DECREF(user_data->send_frame_cb);
    }
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

    free(user_data);
}


int
kaa_get_visual_info(Xine_PyObject *xine, PyObject *kwargs, void **visual_return, 
                    driver_info_common **driver_info_return)
{
    kaa_visual_t vis;
    vo_driver_t *passthrough_driver;
    kaa_vo_user_data *user_data;
    PyObject *o, *passthrough = NULL, *control_return = NULL, 
             *send_frame_cb_pyobject = NULL, *osd_configure_cb_pyobject = NULL;
    void *passthrough_visual;
    driver_info_common *passthrough_driver_info;
    int passthrough_visual_type, buflen = -1;

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
    passthrough_driver_info->driver = passthrough_driver;

    if (!passthrough_driver) {
        PyErr_Format(xine_error, "Failed to initialize passthrough driver: %s", PyString_AsString(passthrough));
        return 0;
    }

    memset(&vis, 0, sizeof(vis));
    vis.send_frame_cb           = send_frame_cb;
    vis.osd_configure_cb        = osd_configure_cb;
    vis.passthrough_driver      = PyString_AsString(passthrough);
    vis.passthrough_visual_type = passthrough_visual_type;
    vis.passthrough_visual      = passthrough_visual;
    vis.passthrough             = passthrough_driver;

    if (PyMapping_HasKeyString(kwargs, "osd_buffer")) {
        o = PyDict_GetItemString(kwargs, "osd_buffer");
        if (PyNumber_Check(o))
            vis.osd_buffer = (uint8_t *)PyLong_AsLong(o);
        else {
            if (PyObject_AsWriteBuffer(o, (void **)&vis.osd_buffer, &buflen) == -1)
                return 0;
        }
    }

    if (PyMapping_HasKeyString(kwargs, "osd_stride"))
        if (!PyArg_Parse(PyDict_GetItemString(kwargs, "osd_stride"), "l", &vis.osd_stride))
            return 0;

    if (PyMapping_HasKeyString(kwargs, "osd_rows"))
        if (!PyArg_Parse(PyDict_GetItemString(kwargs, "osd_rows"), "l", &vis.osd_rows))
            return 0;

    if (PyMapping_HasKeyString(kwargs, "send_frame_cb")) {
        o = PyDict_GetItemString(kwargs, "send_frame_cb");
        if (!PyCallable_Check(o)) {
            PyErr_Format(PyExc_ValueError, "send_frame_cb must be callable");
            return 0;
        }
        send_frame_cb_pyobject = o;
        Py_INCREF(o);
    }

    if (PyMapping_HasKeyString(kwargs, "osd_configure_cb")) {
        o = PyDict_GetItemString(kwargs, "osd_configure_cb");
        if (!PyCallable_Check(o)) {
            PyErr_Format(PyExc_ValueError, "osd_configure_cb must be callable");
            return 0;
        }
        osd_configure_cb_pyobject = o;
        Py_INCREF(o);
    }

    if (vis.osd_buffer && buflen != -1 && buflen != vis.osd_stride * vis.osd_rows) {
        PyErr_Format(PyExc_ValueError, "OSD buffer length does not match supplied stride * rows");
        return 0;
    }

    Py_INCREF(passthrough);

    user_data = malloc(sizeof(kaa_vo_user_data));
    memset(user_data, 0, sizeof(kaa_vo_user_data));
    user_data->passthrough_pyobject    = passthrough;
    user_data->send_frame_cb           = send_frame_cb_pyobject;
    user_data->osd_configure_cb        = osd_configure_cb_pyobject;
    user_data->common.dealloc_cb       = kaa_driver_dealloc;
    user_data->passthrough_visual      = passthrough_visual;
    user_data->passthrough_driver_info = passthrough_driver_info;

    vis.send_frame_cb_data    = user_data;
    vis.osd_configure_cb_data = user_data;

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

