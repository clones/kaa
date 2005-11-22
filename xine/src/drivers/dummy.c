#include "dummy.h"
#include "video_out_dummy.h"

typedef struct _dummy_vo_user_data {
    driver_info_common common;

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


int
dummy_get_visual_info(Xine_PyObject *xine, PyObject *kwargs, void **visual_return,
                     driver_info_common **driver_info_return)
{
    dummy_visual_t vis;
    dummy_vo_user_data *user_data;
    PyObject *frobate = NULL;

    // Handle driver-specific kwargs here ...
    frobate = PyDict_GetItemString(kwargs, "frobate");
    if (!frobate || !PyInt_Check(frobate)) {
        PyErr_Format(xine_error, "Dummy driver needs the frobate object and it must be int.");
        return 0;
    }

    user_data = malloc(sizeof(dummy_vo_user_data));
    user_data->common.dealloc_cb = dummy_driver_dealloc;
    user_data->frobate = frobate;
    // Hold a reference to the driver-specific objects  ...
    Py_INCREF(frobate);

    vis.frobate = PyLong_AsLong(frobate);

    *visual_return = malloc(sizeof(vis));
    memcpy(*visual_return, &vis, sizeof(vis));
    *driver_info_return = (driver_info_common *)user_data;
    return 1;
}
