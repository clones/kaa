# plugindir is set in configure

# change libgstplugin.la to something more suitable
plugin_LTLIBRARIES = libgstdvbtuner.la

# for the next set of variables, rename the prefix if you renamed the .la

# sources used to compile this plug-in
libgstdvbtuner_la_SOURCES = gstdvbtuner.c

# flags used to compile this plugin
# add other _CFLAGS and _LIBS as needed
libgstdvbtuner_la_CFLAGS = $(GST_CFLAGS) -Werror
libgstdvbtuner_la_LIBADD = $(GST_LIBS)
libgstdvbtuner_la_LDFLAGS = $(GST_PLUGIN_LDFLAGS)

# headers we need but don't want installed
noinst_HEADERS = gstdvbtuner.h
