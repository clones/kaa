#ifndef __COMMON_H_
#define __COMMON_H_
#include "../xine.h"

typedef struct _driver_info_common {
    void (*dealloc_cb)(void *);
    vo_driver_t *driver;
} driver_info_common;

int driver_get_visual_info(Xine_PyObject *xine, char *driver, PyObject *kwargs, int *visual_type_return,
                           void **visual_return, driver_info_common **driver_info_return);

#endif

