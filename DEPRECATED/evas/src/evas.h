/*
 * ----------------------------------------------------------------------------
 * evas.h
 * ----------------------------------------------------------------------------
 * $Id$
 *
 * ----------------------------------------------------------------------------
 * kaa.evas - An evas wrapper for Python
 * Copyright (C) 2006 Jason Tackaberry <tack@sault.org>
 *
 * First Edition: Jason Tackaberry <tack@sault.org>
 * Maintainer:    Jason Tackaberry <tack@sault.org>
 *
 * Please see the file AUTHORS for a complete list of authors.
 *
 * This library is free software; you can redistribute it and/or modify
 * it under the terms of the GNU Lesser General Public License version
 * 2.1 as published by the Free Software Foundation.
 *
 * This library is distributed in the hope that it will be useful, but
 * WITHOUT ANY WARRANTY; without even the implied warranty of
 * MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
 * Lesser General Public License for more details.
 *
 * You should have received a copy of the GNU Lesser General Public
 * License along with this library; if not, write to the Free Software
 * Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA
 * 02110-1301 USA
 *
 * ----------------------------------------------------------------------------
 */

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
extern unsigned long long __benchmark_start, __benchmark_end;
extern unsigned long long __benchmark_time;

#define rdtscll(val) \
     __asm__ __volatile__("rdtsc" : "=A" (val));

#define BENCH_START rdtscll(__benchmark_start)
#define BENCH_END  { \
     rdtscll(__benchmark_end); \
     __benchmark_time += __benchmark_end - __benchmark_start; \
}

#else
#define BENCH_START {}
#define BENCH_END {}
#endif

#endif

