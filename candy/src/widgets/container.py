# -*- coding: iso-8859-1 -*-
# -----------------------------------------------------------------------------
# container.py - Group Widgets
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

__all__ = [ 'Group', 'LayoutGroup', 'Container' ]

# python imports
import logging

# kaa imports
import kaa
from kaa.utils import property

# kaa.candy imports
from ..core import is_template
from .. import backend
from widget import Widget

# get logging object
log = logging.getLogger('kaa.candy')

class Group(Widget):
    """
    Group widget.
    """
    def __init__(self, pos=None, size=None, context=None):
        """
        Simple clutter.Group widget

        @param pos: (x,y) position of the widget or None
        @param size: (width,height) geometry of the widget or None. A clutter.Group
            does not respect the given geometry. If set, the geometry can be
            read with the get_max memeber functions.
        @param context: the context the widget is created in
        """
        super(Group, self).__init__(pos, size, context)
        self.children = []
        self.__children_added = []
        self.__children_removed = []
        self.__children_restack = []

    def get_widget(self, name):
        """
        Get child element with the given name. For group children this
        function will search recursive.

        @param name: name of the child
        @returns: widget or None
        """
        for child in self.children:
            if child.name == name:
                return child
            if isinstance(child, Group):
                result = child.get_element(name)
                if result is not None:
                    return result
        return None

    def _candy_render(self):
        """
        Render the widget
        """
        if self._obj is None:
            self._obj = backend.Group()
            self._obj.show()
        # sync removed children
        while self.__children_removed:
            self._sync_layout = True
            child = self.__children_removed.pop(0)
            if child.parent is None:
                child._sync_properties['parent'] = None
                child._candy_sync_properties()
        # prepare new children
        while self.__children_added:
            self.__children_added.pop(0)._sync_properties['parent'] = self._obj
        # sync all children
        for child in self.children:
            if child._sync_required:
                # require layout when a child changes layout
                self._sync_layout = self._sync_layout or child._sync_layout
                child._candy_sync()
        # restack children
        while self.__children_restack:
            child, direction = self.__children_restack.pop(0)
            if direction == 'top':
                child._obj.raise_top()
            if direction == 'bottom':
                child._obj.lower_bottom()

    def _child_add(self, child):
        """
        Add a child and set it visible.

        @param child: child widget
        """
        self._queue_sync(rendering=True)
        self.__children_added.append(child)
        self.children.append(child)

    def _child_remove(self, child):
        """
        Remove a child widget

        @param child: child widget
        """
        if child in self.__children_added:
            self.__children_added.remove(child)
        else:
            self.__children_removed.append(child)
        self._queue_sync(rendering=True)
        self.children.remove(child)

    def _child_restack(self, child, direction):
        """
        Restack a child

        @param child: child widget
        @param direction: top or bottom
        """
        self.__children_restack.append((child, direction))


class LayoutGroup(Group):
    """
    Group with additional layout functionality. If a layout function is
    provided this function will be called to layout the children.

    This module also provides two layout functions called horizontal and
    vertical. Additional functions will be added in future versions. It is
    not possible to trigger animations in the layout functions. This would
    result in a recursive call. It is also unclear how an animation should
    work when some items are removed, some added, some resorted and some
    resized. The layout functions are only allowed to set the x and y
    coordinates of a child.
    """
    __padding = 0
    __layout = None
    possible_layouts = {}

    def __init__(self, pos=None, size=None, layout=None, context=None):
        super(LayoutGroup, self).__init__(pos, size, context)
        if layout is not None:
            self.layout = layout

    @property
    def padding(self):
        return self.__padding

    @padding.setter
    def padding(self, padding):
        self.__padding = padding
        self._queue_sync(layout=True)

    @property
    def layout(self):
        return self.__layout

    @layout.setter
    def layout(self, layout):
        if self._obj:
            log.error('FIXME: unable to change layout during runtime')
            return
        if isinstance(layout, str):
            if self.possible_layouts.get(layout) is None:
                log.error('unknown layout %s', layout)
                return
            layout = self.possible_layouts.get(layout)
        self.__layout = layout

    def move_child(self, child, pos):
        """
        Move a child to a specific position in the stack
        """
        self.children.remove(child)
        self.children.insert(pos, child)
        self._queue_sync(layout=True)

    def _candy_sync_layout(self):
        """
        Layout the widget
        """
        super(LayoutGroup, self)._candy_sync_layout()
        if self.__layout:
            self.__layout(self.children, self.padding)
            for child in self.children:
                if child._sync_layout:
                    child._candy_sync_layout()

    @classmethod
    def register_layout(cls, name, func):
        """
        Register a layout function to kaa.candy
        """
        cls.possible_layouts[name] = func


def layout_vertical(widgets, padding):
    """
    Simple layout function to sort the widgets vertical
    """
    y = 0
    for widget in widgets:
        widget.y = y
        # FIXME: handle widget.height == 0
        y += widget.height + padding

def layout_horizontal(widgets, padding):
    """
    Simple layout function to sort the widgets horizontal
    """
    x = 0
    for widget in widgets:
        widget.x = x
        # FIXME: handle widget.width == 0
        x += widget.width + padding

# Register the two layout functions
LayoutGroup.register_layout('vertical', layout_vertical)
LayoutGroup.register_layout('horizontal', layout_horizontal)


class Container(LayoutGroup):
    """
    Container widget with other widgets in it.
    """
    candyxml_name = 'container'
    context_sensitive = True

    def __init__(self, pos=None, size=None, widgets=[], dependency=None, context=None):
        """
        Create a container

        @param pos: (x,y) position of the widget or None
        @param size: (width,height) geometry of the widget or None.
        @param widgets: list of widgets or widget templates to put into the container
        @param dependency: list of context dependencies for set_context
        @param context: the context the widget is created in
        """
        super(Container, self).__init__(pos, size, None, context)
        for widget in widgets:
            try:
                if is_template(widget):
                    template = widget
                    widget = template(context)
                    if widget.context_sensitive:
                        widget.userdata['container:template'] = template
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
                   child.userdata.get('container:removing'):
                continue
            try:
                child.userdata['container:removing'] = True
                template = child.userdata.get('container:template')
                if not template:
                    # this only works for items based on templates
                    log.warning('unable to replace child %s', child)
                    continue
                new = template(context)
                new.userdata['container:template'] = template
                self._child_replace(child, new)
            except:
                log.exception('render')

    def _child_replace(self, old, new):
        """
        Replace child with a new one. This function is a callback from
        set_context in case the container wants to add some animations.
        """
        old.parent = None
        new.parent = self

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
