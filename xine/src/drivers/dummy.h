#ifndef _DUMMY_H_
#define _DUMMY_H_

#include <Python.h>
#include "../xine.h"
#include "../vo_driver.h"

Xine_VO_Driver_PyObject *dummy_open_video_driver(Xine_PyObject *, PyObject *kwargs);

#endif
