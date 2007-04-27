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
# Copyright (C) 2006 Dirk Meyer
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

# kaa imports
from kaa.notifier import MainThreadCallback, is_mainthread

engines = []

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


def _get_engine(template, engine):
    """
    Get the engine object for the given template. If engine is given, use
    that as name to find the engine.
    """
    if not engine:
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


def expose(template=None, engine=None, mainloop=True):
    """
    Expose function / wrapper. It adds the possiblity to define a template
    for the function and executes the callback from the mainloop.
    """

    if template:
        engine = _get_engine(template, engine)

    def decorator(func):

        def newfunc(self, *args, **kwargs):
            _function = func
            if mainloop and not is_mainthread():
                _function = MainThreadCallback(func)
                _function.set_async(False)
            result = _function(self, *args, **kwargs)
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
