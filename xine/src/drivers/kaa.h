#ifndef _KAA_H_
#define _KAA_H_

#include <Python.h>
#include "../xine.h"
#include "common.h"

int kaa_get_visual_info(Xine_PyObject *xine, PyObject *kwargs, void **visual_return, 
                        driver_info_common **driver_info_return);

#endif
