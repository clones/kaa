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
