/*
 * ----------------------------------------------------------------------------
 * GStreamer Transport Stream Splitter
 * ----------------------------------------------------------------------------
 * $Id$
 *
 * ----------------------------------------------------------------------------
 * kaa.record - Recording Module based on GStreamer
 * Copyright (C) 2007 Sönke Schwardt, Dirk Meyer
 *
 * First Edition: Sönke Schwardt <bulk@schwardtnet.de>
 * Maintainer:    Sönke Schwardt <bulk@schwardtnet.de>
 *
 * Please see the file AUTHORS for a complete list of authors.
 *
 * This program is free software; you can redistribute it and/or modify
 * it under the terms of the GNU General Public License as published by
 * the Free Software Foundation; either version 2 of the License, or
 * (at your option) any later version.
 *
 * This program is distributed in the hope that it will be useful, but
 * WITHOUT ANY WARRANTY; without even the implied warranty of MER-
 * CHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the GNU General
 * Public License for more details.
 *
 * You should have received a copy of the GNU General Public License along
 * with this program; if not, write to the Free Software Foundation, Inc.,
 * 59 Temple Place, Suite 330, Boston, MA 02111-1307 USA
 *
 * ----------------------------------------------------------------------------
 */

#ifndef __GST_TSSPLITTER_H__
#define __GST_TSSPLITTER_H__

#include <sys/time.h>
#include <time.h>

#include <gst/gst.h>

G_BEGIN_DECLS

/* #defines don't like whitespacey bits */
#define GST_TYPE_TSSPLITTER \
  (gst_tssplitter_get_type())
#define GST_TSSPLITTER(obj) \
  (G_TYPE_CHECK_INSTANCE_CAST((obj),GST_TYPE_TSSPLITTER,GstTSSplitter))
#define GST_TSSPLITTER_CLASS(klass) \
  (G_TYPE_CHECK_CLASS_CAST((klass),GST_TYPE_TSSPLITTER,GstTSSplitterClass))
/* #define GST_IS_PLUGIN_TEMPLATE(obj) \ */
/*   (G_TYPE_CHECK_INSTANCE_TYPE((obj),GST_TYPE_TSSPLITTER)) */
/* #define GST_IS_PLUGIN_TEMPLATE_CLASS(klass) \ */
/*   (G_TYPE_CHECK_CLASS_TYPE((klass),GST_TYPE_TSSPLITTER)) */

#define DEBUGf( fmt, args... ) \
   do { \
     if (filter->debug_output) { \
       struct timeval tv;                                           \
       gettimeofday( &tv, NULL );                                   \
       struct tm *curtime;                                          \
       time_t now = time(NULL);                                     \
       curtime = localtime( &now );                                 \
       g_print( "\n%02d:%02d:%02d.%03d %10s:%04d (%s): " fmt,           \
                curtime->tm_hour, curtime->tm_min, curtime->tm_sec, ((int)tv.tv_usec / 1000),  \
                __FILE__, __LINE__, __FUNCTION__, ##args);                       \
     } \
   } while(0);


#define GST_TSSPLITTER_INIT_FILTERLIST_LEN    5

typedef struct _GstTSSplitter       GstTSSplitter;
typedef struct _GstTSSplitterClass  GstTSSplitterClass;
typedef struct _GstTSSplitterFilter GstTSSplitterFilter;


struct _GstTSSplitterFilter
{
  char *name;
  char *pidlist;
  GstPad *pad;
};

struct _GstTSSplitter
{
  GstElement element;

  GstPad *sinkpad, *srcpad;

  GstBuffer *inbuffer;

  gboolean             debug_output;
  gboolean             signal_new_pids;
  gint                 filterlist_len;
  gint                 filterlist_free;
  GstTSSplitterFilter *filterlist;
};

struct _GstTSSplitterClass
{
  GstElementClass parent_class;

  void          (*set_filter)          (GstTSSplitter *filter, char *name, char* pidlist);
  void          (*remove_filter)       (GstTSSplitter *filter, char *name);
};

GType gst_tssplitter_get_type (void);

G_END_DECLS

#endif /* __GST_TSSPLITTER_H__ */
