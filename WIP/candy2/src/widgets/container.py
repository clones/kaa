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

# python imports
import logging

# kaa imports
import kaa

# gui imports
import kaa.candy
import core

# get logging object
log = logging.getLogger('gui')

class Container(core.Group):
    """
    Container widget with other widgets in it.
    """
    __gui_name__ = 'container'
    context_sensitive = True

    def __init__(self, pos, size, widgets, dependency=None, context=None):
        super(Container, self).__init__(pos, size, context)
        for template in widgets:
            try:
                child = template(context)
                if child.context_sensitive:
                    child.set_userdata('template', template)
                self.add(child)
            except:
                log.exception('render')
        if dependency and context:
            self.set_dependency(*dependency)

    def set_context(self, context):
        """
        Set a new context for the widget and redraw it.
        """
        super(Container, self).set_context(context)
        for child in self.get_children()[:]:
            if not child.context_sensitive or child.try_context(context) or \
                   child.get_userdata('removing'):
                continue
            try:
                # FIXME: this code needs some updates
                child.set_userdata('removing', True)
                template = child.get_userdata('template')
                new = template(context)
                new.set_userdata('template', template)
                self.add(new)
                a1 = child.animate('hide', context=context) or []
                a2 = new.animate('show', context=context) or []
                self.remove(child, kaa.InProgressList(a1 + a2))
            except:
                log.exception('render')
                
    def get_element(self, name):
        """
        Get child element with the given name.
        """
        for child in self.get_children():
            if child.get_name() == name:
                return child
            if isinstance(child, Container):
                result = child.get_element(name)
                if result is not None:
                    return result
        return None

    def remove(self, child, delay=None):
        """
        Remove the given child and hide it.
        """
        if delay is not None and not delay.is_finished():
            return delay.connect_once(self.remove, child).set_ignore_caller_args()
        child.hide()
        super(Container, self).remove(child)

    @classmethod
    def parse_XML(cls, element):
        """
        Parse the XML element for parameter to create the widget.
        """
        widgets = []
        for child in element:
            w = child.xmlcreate()
            if not w:
                log.error('unable to parse %s', child.node)
            else:
                widgets.append(w)
        return super(Container, cls).parse_XML(element).update(
            dependency=(element.depends or '').split(' '),
            widgets=widgets)


# register widgets to the core
kaa.candy.xmlparser.register(Container)
