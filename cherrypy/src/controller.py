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

# kid import
import kid

# kaa imports
from kaa.notifier import MainThreadCallback

# enable importing kid files as python modules
kid.enable_import()


def expose(template=None, mainloop=True):
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
            return _function(self, template, func, *args, **kwargs)

        try:
            newfunc.func_name = func.func_name
        except TypeError:
            pass
        newfunc.exposed = True
        return newfunc

    return decorator


def _execute_func(self, template, func, *args, **kwargs):
    """
    Helper function to call the function and handle kid. This whole function
    will be called from the main thread (when mainloop==True)
    """
    if not template:
        return func(self, *args, **kwargs)
    template = kid.Template(file=template)
    result = func(self, template, *args, **kwargs)
    if result:
        for key, value in result.items():
            setattr(template, key, value)
    return template.serialize(output='xhtml')
