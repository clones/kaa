#include "dummy.h"
#include "video_out_dummy.h"

typedef struct _dummy_vo_user_data {
    // Driver-specific VODriver data here ....
    PyObject *frobate;
} dummy_vo_user_data;


void
dummy_driver_dealloc(void *data)
{
    PyGILState_STATE gstate;
    dummy_vo_user_data *user_data = (dummy_vo_user_data *)data;
 
    gstate = PyGILState_Ensure();
    // Finalization for driver-specific data (decref any pyobjects, etc.)
    Py_DECREF(user_data->frobate);
    PyGILState_Release(gstate);
    free(user_data);
}


Xine_VO_Driver_PyObject *
dummy_open_video_driver(Xine_PyObject *xine, PyObject *kwargs)
{
    dummy_visual_t vis;
    vo_driver_t *driver;
    dummy_vo_user_data *user_data;
    PyObject *frobate = NULL;
    Xine_VO_Driver_PyObject *vo_driver_pyobject;

    // Handle driver-specific kwargs here ...
    frobate = PyDict_GetItemString(kwargs, "frobate");
    if (!frobate || !PyInt_Check(frobate)) {
        PyErr_Format(xine_error, "Dummy driver needs the frobate object and it must be int.");
        return NULL;
    }

    user_data = malloc(sizeof(dummy_vo_user_data));
    user_data->frobate = frobate;
    // Hold a reference to the driver-specific objects  ...
    Py_INCREF(frobate);

    vis.frobate = PyLong_AsLong(frobate);

    driver = _x_load_video_output_plugin(xine->xine, "dummy", XINE_VISUAL_TYPE_NONE, (void *)&vis);
    if (!driver) {
        PyErr_Format(xine_error, "Internal error while loading video driver");
        return NULL;
    }

    vo_driver_pyobject = pyxine_new_vo_driver_pyobject(xine, xine->xine, driver, 1);
    vo_driver_pyobject->dealloc_cb = dummy_driver_dealloc;
    vo_driver_pyobject->dealloc_data = user_data;

    return vo_driver_pyobject;
}
