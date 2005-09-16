#ifndef _KAA_H_
#define _KAA_H_

#include <Python.h>
#include "../xine.h"
#include "../vo_driver.h"

vo_driver_t *kaa_open_video_driver(Xine_PyObject *, PyObject *kwargs, void **);
void kaa_open_video_driver_finalize(Xine_VO_Driver_PyObject *, void *);

#endif
