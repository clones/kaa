#ifndef _KAA_H_
#define _KAA_H_

#include <Python.h>
#include "../xine.h"
#include "../vo_driver.h"

Xine_VO_Driver_PyObject *kaa_open_video_driver(Xine_PyObject *, PyObject *kwargs);

#endif
