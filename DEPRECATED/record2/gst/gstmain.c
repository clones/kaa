/*
 * ----------------------------------------------------------------------------
 * Main GStreamer Module for kaa.record
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

#include "config.h"

#include <gst/gst.h>

#include "gstdvbtuner.h"
#include "gsttssplitter.h"

GST_DEBUG_CATEGORY (kaa_debug);
#define GST_CAT_DEFAULT kaa_debug

static gboolean
plugin_init (GstPlugin * plugin)
{
  GST_DEBUG_CATEGORY_INIT (kaa_debug, "kaa", 0,
      "special elements for processing dvb/video cards - used by kaa");

  return gst_element_register (plugin, "tssplitter",
      GST_RANK_NONE, GST_TYPE_TSSPLITTER) &&
      gst_element_register (plugin, "dvbtuner",
      GST_RANK_NONE, GST_TYPE_DVBTUNER);
}

GST_PLUGIN_DEFINE (GST_VERSION_MAJOR,
    GST_VERSION_MINOR,
    "kaarecord",
    "Plugin contains kaa specific plugins for dvb cards and video stream processing",
    plugin_init, VERSION, "LGPL", "KaaRecord", "http://www.freevo.org/kaa")
