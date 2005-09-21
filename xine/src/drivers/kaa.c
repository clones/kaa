#include "kaa.h"
#include "video_out_kaa.h"

typedef struct _kaa_vo_user_data {
    kaa_driver_t *driver;
    PyObject *send_frame_cb, *osd_configure_cb,
             *passthrough_pyobject;
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
    char *command;

    if (!PyArg_ParseTuple(args, "s|O", &command, &cmd_arg))
        return NULL;

    #define type_check(var, tp, errmsg) \
        if (!var || !Py ## tp ## _Check(var)) { PyErr_Format(xine_error, errmsg); return NULL;}
    #define gui_send(cmd, val) \
        user_data->driver->vo_driver.gui_data_exchange(&user_data->driver->vo_driver, GUI_SEND_KAA_VO_ ## cmd, (void *)val);

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
        struct { int x, y, w, h; } r;
        if (!PyArg_ParseTuple(cmd_arg, "iiii", &r.x, &r.y, &r.w, &r.h))
            return NULL;
        gui_send(OSD_INVALIDATE_RECT, &r);
    }
    else if (!strcmp(command, "set_osd_slice")) {
        struct { int y, h; } slice;
        if (!PyArg_ParseTuple(cmd_arg, "ii", &slice.y, &slice.h))
            return NULL;
        gui_send(OSD_SET_SLICE, &slice);
    }
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
    free(user_data);
}


Xine_VO_Driver_PyObject *
kaa_open_video_driver(Xine_PyObject *xine, PyObject *kwargs)
{
    kaa_visual_t vis;
    vo_driver_t *driver;
    kaa_vo_user_data *user_data;
    PyObject *o, *passthrough = NULL, *control_return = NULL, 
             *send_frame_cb_pyobject = NULL, *osd_configure_cb_pyobject = NULL;
    Xine_VO_Driver_PyObject *vo_driver_pyobject;
    int buflen = -1;

    passthrough = PyDict_GetItemString(kwargs, "passthrough");
    if (!passthrough || !Xine_VO_Driver_PyObject_Check(passthrough)) {
        PyErr_Format(xine_error, "Passthrough must be a VODriver object");
        return NULL;
    }

    memset(&vis, 0, sizeof(vis));
    vis.send_frame_cb           = send_frame_cb;
    vis.osd_configure_cb        = osd_configure_cb;
    vis.passthrough             = ((Xine_VO_Driver_PyObject *)passthrough)->driver;

    if (PyMapping_HasKeyString(kwargs, "osd_buffer")) {
        o = PyDict_GetItemString(kwargs, "osd_buffer");
        if (PyNumber_Check(o))
            vis.osd_buffer = (uint8_t *)PyLong_AsLong(o);
        else {
            if (PyObject_AsWriteBuffer(o, (void **)&vis.osd_buffer, &buflen) == -1)
                return NULL;
        }
    }

    if (PyMapping_HasKeyString(kwargs, "osd_stride"))
        if (!PyArg_Parse(PyDict_GetItemString(kwargs, "osd_stride"), "l", &vis.osd_stride))
            return NULL;

    if (PyMapping_HasKeyString(kwargs, "osd_rows"))
        if (!PyArg_Parse(PyDict_GetItemString(kwargs, "osd_rows"), "l", &vis.osd_rows))
            return NULL;

    if (PyMapping_HasKeyString(kwargs, "send_frame_cb")) {
        o = PyDict_GetItemString(kwargs, "send_frame_cb");
        if (!PyCallable_Check(o)) {
            PyErr_Format(PyExc_ValueError, "send_frame_cb must be callable");
            return NULL;
        }
        send_frame_cb_pyobject = o;
        Py_INCREF(o);
    }

    if (PyMapping_HasKeyString(kwargs, "osd_configure_cb")) {
        o = PyDict_GetItemString(kwargs, "osd_configure_cb");
        if (!PyCallable_Check(o)) {
            PyErr_Format(PyExc_ValueError, "osd_configure_cb must be callable");
            return NULL;
        }
        osd_configure_cb_pyobject = o;
        Py_INCREF(o);
    }

    if (vis.osd_buffer && buflen != -1 && buflen != vis.osd_stride * vis.osd_rows) {
        PyErr_Format(PyExc_ValueError, "OSD buffer length does not match supplied stride * rows");
        return NULL;
    }

    Py_INCREF(passthrough);

    user_data = malloc(sizeof(kaa_vo_user_data));
    memset(user_data, 0, sizeof(kaa_vo_user_data));
    user_data->passthrough_pyobject = passthrough;
    user_data->send_frame_cb        = send_frame_cb_pyobject;
    user_data->osd_configure_cb     = osd_configure_cb_pyobject;

    vis.send_frame_cb_data    = user_data;
    vis.osd_configure_cb_data = user_data;

    driver = _x_load_video_output_plugin(xine->xine, "kaa", XINE_VISUAL_TYPE_NONE, (void *)&vis);
    user_data->driver = (kaa_driver_t *)driver;
    
    control_return = PyDict_GetItemString(kwargs, "control_return");
    if (control_return && PyList_Check(control_return)) {
        PyObject *py_ud = PyCObject_FromVoidPtr((void *)user_data, NULL);
        PyObject *control = PyCFunction_New(&control_def, py_ud);
        PyList_Append(control_return, control);
        Py_DECREF(control);
        Py_DECREF(py_ud);
    }

    vo_driver_pyobject = pyxine_new_vo_driver_pyobject(xine, xine->xine, driver, 1);
    vo_driver_pyobject->dealloc_cb = kaa_driver_dealloc;
    vo_driver_pyobject->dealloc_data = user_data;

    return vo_driver_pyobject;
}

