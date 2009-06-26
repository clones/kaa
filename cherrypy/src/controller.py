# -*- coding: iso-8859-1 -*-
# -----------------------------------------------------------------------------
# controller.py - Improved expose function for CherryPy classes
# -----------------------------------------------------------------------------
# $Id$
#
# This module define the expose decorator. The idea is copied from TurboGears.
# The expose function adds a template (Kid or Cheetah) and it is possible to
# execute the function from the main thread.
#
# -----------------------------------------------------------------------------
# kaa.cherrypy - Web Framework for Kaa based on CherryPy
# Copyright (C) 2006,2008 Dirk Meyer
#
# First Edition: Dirk Meyer <dmeyer@tzi.de>
# Maintainer:    Dirk Meyer <dmeyer@tzi.de>
#
# This library is free software; you can redistribute it and/or modify
# it under the terms of the GNU Lesser General Public License version
# 2.1 as published by the Free Software Foundation.
#
# This library is distributed in the hope that it will be useful, but
# WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
# Lesser General Public License for more details.
#
# You should have received a copy of the GNU Lesser General Public
# License along with this library; if not, write to the Free Software
# Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA
# 02110-1301 USA
#
# -----------------------------------------------------------------------------

__all__ = [ 'expose', 'Template', 'template', 'thread_template' ]

# python imports
import types
import os
import traceback
import cherrypy
import time

# kaa imports
import kaa
from kaa import strutils

engines = []
default_engine = None

# load template engines
# TODO: support being installed as an egg
for f in os.listdir(os.path.dirname(__file__)):
    if not f.startswith('templ_') or not f.endswith('.py'):
        # this is no template engine
        continue
    try:
        # try to import
        exec('from %s import Template as Engine' % f[:-3])
        # add to list of engines
        engines.append(Engine())
    except ImportError:
        # engine not supported
        pass


def set_default_engine(engine):
    """
    Sets the template engine to use when no engine is explicitly specified
    in expose decorator.
    """
    global default_engine
    for e in engines:
        if e.name == engine:
            default_engine = e
            return
    raise ValueError('Unknown engine "%s"' % engine)


def _get_engine(template, engine):
    """
    Get the engine object for the given template. If engine is given, use
    that as name to find the engine.
    """
    if not engine:

        if default_engine:
            # Default engine was specified, so return that.
            return default_engine

        # get engine by detecting the type
        for e in engines:
            if e.detect(template):
                return e
        raise RuntimeError('unable to detect template engine for %s' % template)

    for e in engines:
        # get engine by name
        if e.name == engine:
            return e
    raise RuntimeError('unable to detect template engine for %s' % template)


def expose(template=None, engine=None, mainloop=False, content_type='text/html', cache=None, json=False):
    """
    Decorator used to expose functions to HTTP requests.  This decorator is 
    similar to cherrypy's native expose decorator, but adds the following
    functionality:

        template: path pointing to a template to display for the request.  If
                  path is relative, it will be relative to the location of the
                  file calling the expose decorator.
          engine: template engine to use to evaluate template.  If None, the
                  engine will be detected, unless set_default_engine() was called,
                  and in that case the default engine will be used.
        mainloop: if True, decorated function will execute in the main thread.  If
                  False, decorated function is executed in the cherrypy handler
                  thread.
    content_type: value to use for the Content-Type header in the HTTP response
           cache: number of hours to cache the page.  0 will prevent client from
                  caching; None will not send cache headers.
            json: encodes the return value of the decorated function as JSON
                  and sends to client as text/plain.  The JSON data is prefixed
                  with '{}&& ' to thwart JSON hijacking; the client will 
                  therefore be required to strip this prefix before parsing.
                  Requires python-json to be installed.
    """

    if template:
        if not template.startswith('/'):
            # Template path is relative; convert to absolute path, which is
            # relative to the location of the file calling the expose
            # decorator.
            caller_dir = os.path.dirname(os.path.realpath(traceback.extract_stack()[-2][0]))
            template = os.path.join(caller_dir, template)
        if engine != 'raw':
            engine = _get_engine(template, engine)

    def decorator(func):

        def newfunc(self, *args, **kwargs):
            # FIXME: should get supported charsets from request
            charset = cherrypy.config.get('charset', 'utf-8')

            # Set content-type before calling handler to give handler a chance
            # to override it.
            if not json:
                cherrypy.serving.response.headers['Content-Type'] = '%s; charset=%s' % (content_type, charset)

            if engine == 'raw' and template:
                from cherrypy.lib.static import serve_file
                return serve_file(template, content_type=content_type)

            # We pass this context as the first arg to each handler.  The
            # reason is that in cherrypy, the request and response objects are
            # dependent on which thread they are being accessed from.  So if
            # the handler wants to modify the response.headers dict and that
            # handler is being called from the main thread, it cannot access
            # cherrypy.response.headers because this is the response object for
            # the main thread, not the current thread.
            class ctx:
                request = cherrypy.serving.request
                response = cherrypy.serving.response

            if mainloop and not kaa.is_mainthread():
                result = kaa.MainThreadCallable(func)(self, ctx, *args, **kwargs).wait()
            else:
                result = func(self, ctx, *args, **kwargs)

            if cache is not None:
                seconds = int(cache * 60 * 60)
                if seconds != 0:
                    gmtime = time.gmtime(time.time() + seconds)
                    ctx.response.headers['Expires'] = time.strftime('%a, %d %b %Y %H:%M:%S GMT', gmtime)
                    ctx.response.headers['Cache-Control'] = 'public, max-age=%d' % seconds
                else:
                    ctx.response.headers['Cache-Control'] = 'no-cache, must-revalidate'

            if json:
                # Handle JSON response.
                import json as pyjson
                # Do not set charset here, it breaks IE.  Yes, seriously.
                ctx.response.headers['Content-Type'] = 'text/plain'
                return '{}&& ' + pyjson.write(result).encode(charset)

            if not template:
                return strutils.to_unicode(result).encode(charset)
            # Engine should return a string encoded with charset
            return engine.parse(template, charset, result)

        try:
            newfunc.func_name = func.func_name
        except TypeError:
            pass
        newfunc.exposed = True
        newfunc.template = template
        return newfunc

    return decorator


class Template(object):
    """
    A class wrapping a template. It has a __call__ function to execute
    the template and an exposed render function to use the template as
    full working side in the webserver.
    """
    def __init__(self, template, engine=None):
        self.engine = _get_engine(template, engine)
        self.template = template


    def __call__(self, **attributes):
        """
        Render the template with the given attributes.
        """
        return self.engine.parse(self.template, attributes)


    @expose()
    def render_mainloop(self, **attributes):
        """
        Render the template with the given attributes.
        This function is exposed to run in the main loop.
        """
        return self.engine.parse(self.template, attributes)

    @expose(mainloop=False)
    def render_thread(self, **attributes):
        """
        Render the template with the given attributes.
        This function is exposed to run in a thread
        """
        return self.engine.parse(self.template, attributes)


def template(template, engine=None):
    """
    Return an exposed render function for the template to run in the
    main loop.
    """
    return Template(template, engine).render_mainloop


def thread_template(template, engine=None):
    """
    Return an exposed render function for the template to run in a
    thread.
    """
    return Template(template, engine).render_thread
