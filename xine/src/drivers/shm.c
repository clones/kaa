#include "shm.h"
#include "video_out_shm.h"
#include <fcntl.h>
#include <sys/shm.h>
#include <sys/ipc.h>
#include <malloc.h>
#include "../config.h"

int
shm_get_visual_info(Xine_PyObject *xine, PyObject *kwargs, void **visual_return, 
                    driver_info_common **driver_info_return)
{
    shm_visual_t vis;
    PyObject *fifo = NULL;
    driver_info_common *driver_info;

    fifo = PyDict_GetItemString(kwargs, "fifo");
    if (!fifo || !PyString_Check(fifo)) {
        PyErr_Format(xine_error, "kwarg fifo is required and must be a string");
        return 0;
    }

    if ((vis.fd_notify = open(PyString_AsString(fifo), O_RDWR | O_NONBLOCK)) < 0) {
        PyErr_Format(xine_error, "Failed to open fifo for shm notification");
        return 0;
    }

    driver_info = malloc(sizeof(driver_info_common));
    memset(driver_info, 0, sizeof(driver_info_common));

    *visual_return = malloc(sizeof(vis));
    memcpy(*visual_return, &vis, sizeof(vis));
    *driver_info_return = driver_info;
    return 1;
}

