import sys
import kaa
import dvb
import gst

# ARD (Das Erste) in Bremen
ARD = {
    "frequency":482000000,
    "inversion": "AUTO",
    "bandwidth":str(8),
    "code-rate-hp":"2/3",
    "code-rate-lp":"1/2",
    "modulation":"QAM 16",
    "trans-mode":"8k",
    "guard":str(4),
    "hierarchy":"NONE"
}

ZDF = {
    "frequency":562000000,
    "inversion": "AUTO",
    "bandwidth":str(8),
    "code-rate-hp":"2/3",
    "code-rate-lp":"2/3",
    "modulation":"QAM 16",
    "trans-mode":"8k",
    "guard":str(4),
    "hierarchy":"NONE"
}

kaa.main.select_notifier('generic')
kaa.gobject_set_threaded()

d =dvb.DVB(adapter=0, frontend=0)

# tune to ARD in 0.5 seconds
kaa.OneShotTimer(d.tune, ARD).start(0.5)

# start recording 1 after 1 second from startup and stop 4 seconds later
sink = gst.parse_bin_from_description('queue ! filesink name=sink', True)
sink.get_by_name("sink").set_property('location', 'foo1.ts')
kaa.OneShotTimer(d.get_stream(160).append, sink).start(1.0)
kaa.OneShotTimer(d.get_stream(160).remove, sink).start(5.0)

# start recording 2 after 4 second from startup and stop 1 second later
sink = gst.element_factory_make('filesink')
sink.set_property('location', 'foo2.ts')
kaa.OneShotTimer(d.get_stream(160).append, sink).start(4.0)
kaa.OneShotTimer(d.get_stream(160).remove, sink).start(5.0)

# tune to ZDF after 6 seconds from startup
kaa.OneShotTimer(d.tune, ZDF).start(6)

# start recording 3 after 8 second from startup (ZDF) and stop 2 seconds later
sink = gst.element_factory_make('filesink')
sink.set_property('location', 'zdf.ts')
kaa.OneShotTimer(d.get_stream(514).append, sink).start(8.0)
kaa.OneShotTimer(d.get_stream(514).remove, sink).start(10.0)

# stop with C-c
kaa.main.run()
