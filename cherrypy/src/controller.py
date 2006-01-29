# -*- coding: iso-8859-1 -*-
# -----------------------------------------------------------------------------
# controller.py - Improved expose function for CherryPy classes
# -----------------------------------------------------------------------------
# $Id$
#
# This module define the expose decorator. The idea is copied from TurboGears.
# The expose function adds a template (Kid) and it is possible to execute the
# function from the main thread.
#
# -----------------------------------------------------------------------------
# kaa-cherrypy - Web Framework for Kaa based on CherryPy
# Copyright (C) 2006 Dirk Meyer
#
# First Edition: Dirk Meyer <dmeyer@tzi.de>
# Maintainer:    Dirk Meyer <dmeyer@tzi.de>
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful, but
# WITHOUT ANY WARRANTY; without even the implied warranty of MER-
# CHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the GNU General
# Public License for more details.
#
# You should have received a copy of the GNU General Public License along
# with this program; if not, write to the Free Software Foundation, Inc.,
# 59 Temple Place, Suite 330, Boston, MA 02111-1307 USA
#
# -----------------------------------------------------------------------------

__all__ = [ 'expose', 'Template', 'template', 'thread_template' ]

# python imports
import types
import os

# kaa imports
from kaa.notifier import MainThreadCallback, is_mainthread

engines = []

# Kid template

try:
    # kid import
    import kid

    # enable importing kid files as python modules
    kid.enable_import()

    class KidTemplate(object):

        name = 'kid'

        def detect(self, template):
            if type(template) == str and template.endswith('.kid'):
                return True
            if hasattr(template, 'BaseTemplate') and \
               template.BaseTemplate == kid.BaseTemplate:
                return True
            return False

        def parse(self, template, args):
            if type(template) == types.ModuleType:
                return template.Template(**args).serialize(output='xhtml')
            return kid.Template(file=template, **args).serialize(output='xhtml')

    engines.append(KidTemplate())

except ImportError:
    pass


# Cheetah template

try:
    # import
    import Cheetah.Template

    class CheetahTemplate(object):

        name = 'cheetah'

        def detect(self, template):
            if type(template) == str and template.endswith('.tmpl'):
                return True
            if hasattr(template, '__CHEETAH_src__'):
                c = os.path.splitext(os.path.basename(template.__CHEETAH_src__))[0]
                template.__KaaCherrypyTemplate = getattr(template, c)
                return True
            return False

        def parse(self, template, args):
            if type(template) == types.ModuleType:
                return str(template.__KaaCherrypyTemplate(searchList=[args]))
            return str(Cheetah.Template.Template(file=template, searchList=[args]))

    engines.append(CheetahTemplate())

except ImportError:
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
            _function = _execute_func
            if mainloop and not is_mainthread():
                _function = MainThreadCallback(_execute_func)
                _function.set_async(False)
            return _function(self, template, engine, func, args, kwargs)

        try:
            newfunc.func_name = func.func_name
        except TypeError:
            pass
        newfunc.exposed = True
        newfunc.template = template
        return newfunc

    return decorator



def _execute_func(self, filename, engine, func, args, kwargs):
    """
    Helper function to call the function and handle kid. This whole function
    will be called from the main thread (when mainloop==True)
    """
    if not filename:
        return func(self, *args, **kwargs)
    return engine.parse(filename, func(self, *args, **kwargs))




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
