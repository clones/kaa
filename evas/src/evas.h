#ifndef __EVAS_H_
#define __EVAS_H_
#include "config.h"

#include <Python.h>
#include <Evas.h>

extern PyObject *evas_error;

#define Evas_PyObject_Check(v) ((v)->ob_type == &Evas_PyObject_Type)

typedef struct {
    PyObject_HEAD
    Evas *evas;
    PyObject *dict, *dependencies;
} Evas_PyObject;

extern PyTypeObject Evas_PyObject_Type;
void Evas_PyObject__dealloc(Evas_PyObject *);
PyObject *Evas_PyObject__getattr(Evas_PyObject *, char *);
int Evas_PyObject__setattr(Evas_PyObject *, char *, PyObject *);
int Evas_PyObject__compare(Evas_PyObject *, Evas_PyObject *);

#ifdef BENCHMARK
extern double __benchmark_time;
extern struct timezone __bench_tz;
extern struct timeval __bench_start, __bench_end;

#define BENCH_START {gettimeofday(&__bench_start, &__bench_tz);}
#define BENCH_END { \
    gettimeofday(&__bench_end, &__bench_tz); \
    __benchmark_time += (__bench_end.tv_sec - __bench_start.tv_sec) + \
                        ((__bench_end.tv_usec - __bench_start.tv_usec) / 1000000.0); \
}
#endif


#endif

