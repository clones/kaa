# -*- coding: iso-8859-1 -*-
# -----------------------------------------------------------------------------
# tmpl_cheetah.py - Cheetah template wrapper
# -----------------------------------------------------------------------------
# $Id$
#
# This module define a Cheetah wrapper. It is loaded based on the name starting
# with templ_. To write other template engine wrappers, just dump them
# into this directory.
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

# python imports
import os
import types

# import cheetah
import Cheetah.Template

class Template(object):

    name = 'cheetah'

    def detect(self, template):
        """
        Detect if the given template is a Cheetah template or not.
        """
        if type(template) == str and template.endswith('.tmpl'):
            return True
        if hasattr(template, '__CHEETAH_src__'):
            c = os.path.splitext(os.path.basename(template.__CHEETAH_src__))[0]
            template.__KaaCherrypyTemplate = getattr(template, c)
            return True
        return False


    def parse(self, template, args):
        """
        Parse the template and execute it based on the arguments.
        """
        if type(template) == types.ModuleType:
            return str(template.__KaaCherrypyTemplate(searchList=[args]))
        return str(Cheetah.Template.Template(file=template, searchList=[args]))
