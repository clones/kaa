# -*- coding: iso-8859-1 -*-
# -----------------------------------------------------------------------------
# tmpl_kid.py - Kid template wrapper
# -----------------------------------------------------------------------------
# $Id$
#
# This module define a Kid wrapper. It is loaded based on the name starting
# with templ_. To write other template engine wrappers, just dump them
# into this directory.
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

# python imports
import types

# kid import
import kid

class Template(object):

    name = 'kid'

    def detect(self, template):
        """
        Detect if the given template is a Kid template or not.
        """
        if type(template) == str and template.endswith('.kid'):
            return True
        if hasattr(template, 'BaseTemplate') and \
           template.BaseTemplate == kid.BaseTemplate:
            return True
        return False


    def parse(self, template, charset, args):
        """
        Parse the template and execute it based on the arguments.
        """
        if type(template) == types.ModuleType:
            return template.Template(**args).serialize(encoding=charset, output='xhtml')
        return kid.Template(file=template, **args).serialize(encoding=charset, output='xhtml')
