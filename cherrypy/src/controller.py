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

__all__ = [ 'expose' ]

# kaa imports
from kaa.notifier import MainThreadCallback

engines = {}

# Kid template

try:
    # kid import
    import kid

    # enable importing kid files as python modules
    kid.enable_import()

    def kid_render(template, args):
        return kid.Template(file=template, **args).serialize(output='xhtml')

    engines['kid'] = kid_render

except ImportError:
    pass


# Cheetah template

try:
    # import
    import Cheetah.Template

    def cheetah_render(template, args):
        return str(Cheetah.Template.Template(file=template, searchList=[args]))

    engines['cheetah'] = cheetah_render

except ImportError:
    pass


def expose(template=None, engine=None, mainloop=True):
    """
    Expose function / wrapper. It adds the possiblity to define a template
    for the function and executes the callback from the mainloop.
    """
    def decorator(func):

        def newfunc(self, *args, **kwargs):
            _function = _execute_func
            if mainloop:
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


def render(engine, filename, variables):
    """
    Render template with filename based on the given engine and variables.
    """
    if not engine and filename.endswith('.kid'):
        engine = 'kid'
    return engines[engine](filename, variables)

    
def _execute_func(self, filename, engine, func, args, kwargs):
    """
    Helper function to call the function and handle kid. This whole function
    will be called from the main thread (when mainloop==True)
    """
    if not filename:
        return func(self, *args, **kwargs)
    if not engine and filename.endswith('.kid'):
        engine = 'kid'
    return engines[engine](filename, func(self, *args, **kwargs))
