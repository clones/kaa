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

# kaa.candy imports
import kaa.candy
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
        super(Container, self).__init__(pos, size, context)
        for widget in widgets:
            try:
                if kaa.candy.is_template(widget):
                    template = widget
                    widget = template(context)
                    if widget.context_sensitive:
                        widget.set_userdata('template', template)
                self.add(widget)
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
                # FIXME: only works for templates
                child.set_userdata('removing', True)
                template = child.get_userdata('template')
                new = template(context)
                new.set_userdata('template', template)
                self.add(new)
                a1 = child.animate('hide', context=context) or []
                a2 = new.animate('show', context=context) or []
                self.destroy_child(child, kaa.InProgressList(a1 + a2))
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

    @kaa.candy.threaded()
    def destroy_child(self, child, delay=None):
        """
        Destroy the replaced child
        """
        if delay is not None and not delay.is_finished():
            return delay.connect_once(self.destroy_child, child).set_ignore_caller_args()
        child.destroy()

    @classmethod
    def candyxml_parse(cls, element):
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
        return super(Container, cls).candyxml_parse(element).update(
            dependency=(element.depends or '').split(' '),
            widgets=widgets)


# register widget to the xmlparser
Container.candyxml_register()
