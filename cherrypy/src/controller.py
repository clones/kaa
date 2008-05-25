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

# kaa imports
import kaa

engines = []
default_engine = None

# load template engines
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


def expose(template=None, engine=None, mainloop=False):
    """
    Expose function / wrapper. It adds the possiblity to define a template
    for the function and executes the callback from the mainloop.
    """
    if template:
        if not template.startswith('/'):
            # Template path is relative; convert to absolute path, which is
            # relative to the location of the file calling the expose
            # decorator.
            caller_dir = os.path.dirname(os.path.realpath(traceback.extract_stack()[-2][0]))
            template = os.path.join(caller_dir, template)
        engine = _get_engine(template, engine)

    def decorator(func):

        def newfunc(self, *args, **kwargs):
            _function = func

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
                result = kaa.MainThreadCallback(func)(self, ctx, *args, **kwargs).wait()
            else:
                result = func(self, ctx, *args, **kwargs)
            if not template:
                return result
            return engine.parse(template, result)

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
