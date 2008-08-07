# -*- coding: iso-8859-1 -*-
# -----------------------------------------------------------------------------
# .py -
# -----------------------------------------------------------------------------
# $Id$
#
# -----------------------------------------------------------------------------
# kaa-candy - Third generation Canvas System using Clutter as backend
# Copyright (C) 2008 Dirk Meyer, Jason Tackaberry
#
# First Version: Dirk Meyer <dischi@freevo.org>
# Maintainer:    Dirk Meyer <dischi@freevo.org>
#
# Please see the file AUTHORS for a complete list of authors.
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

__all__ = [ 'Container' ]

# python imports
import logging

# kaa imports
import kaa

# kaa.candy imports
from ..core import is_template
import core

# get logging object
log = logging.getLogger('kaa.candy')

class Container(core.Group):
    """
    Container widget with other widgets in it.
    """
    candyxml_name = 'container'
    context_sensitive = True

    def __init__(self, pos, size, widgets, dependency=None, context=None):
        """
        Create a container
        @param pos: (x,y) position of the widget or None
        @param size: (width,height) geometry of the widget or None.
        @param widgets: list of widgets or widget templates to put into the container
        @param dependency: list of context dependencies for set_context
        @param context: the context the widget is created in
        """
        super(Container, self).__init__(pos, size, context)
        for widget in widgets:
            try:
                if is_template(widget):
                    template = widget
                    widget = template(context)
                    if widget.context_sensitive:
                        widget.userdata['template'] = template
                widget.parent = self
            except:
                log.exception('render')
        if dependency:
            for var in dependency:
                self.eval_context(var)

    def set_context(self, context):
        """
        Set a new context for the container and redraw it.
        @param context: context dict
        """
        super(Container, self).set_context(context)
        for child in self.children[:]:
            if not child.context_sensitive or child.try_context(context) or \
                   child.userdata.get('removing'):
                continue
            try:
                child.userdata['removing'] = True
                template = child.userdata.get('template')
                if not template:
                    # this only works for items based on templates
                    log.warning('unable to replace child %s', child)
                    continue
                new = template(context)
                new.userdata['template'] = template
                new.parent = self
                # FIXME: add hide/show animations
                child.destroy()
            except:
                log.exception('render')

    def get_element(self, name):
        """
        Get child element with the given name. For container as child elements this
        function will search recursive.
        @param name: name of the child
        @returns: widget or None
        """
        for child in self.children:
            if child.name == name:
                return child
            if isinstance(child, Container):
                result = child.get_element(name)
                if result is not None:
                    return result
        return None

    @classmethod
    def candyxml_parse(cls, element):
        """
        Parse the candyxml element for parameter to create the widget. Example::
            <container x='10' y='0' width='200' height=100'>
                <child_widget1/>
                <child_widget2/>
            </container>
        """
        widgets = []
        for child in element:
            w = child.xmlcreate()
            if not w:
                log.error('unable to parse %s', child.node)
            else:
                widgets.append(w)
        dependency=(element.depends or '').split(' ')
        while '' in dependency:
            dependency.remove('')
        return super(Container, cls).candyxml_parse(element).update(
            dependency=dependency, widgets=widgets)


# register widget to candyxml
Container.candyxml_register()
