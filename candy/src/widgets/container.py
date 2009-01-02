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
import _weakref

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
                result = child.get_widget(name)
                if result is not None:
                    return result
        return None

    def add(self, *widgets):
        """
        Add widgets to the group.
        """
        for widget in widgets:
            if widget.parent:
                widget.parent.remove(widget)
            # wire widget to ourself
            widget._candy__parent = _weakref.ref(self)
            self.__children_added.append(widget)
            self.children.append(widget)
        self._queue_rendering()
        self._queue_sync_properties('children')

    def remove(self, *widgets):
        """
        Remove widgets from the group.
        """
        for widget in widgets:
            if widget in self.__children_added:
                self.__children_added.remove(widget)
            else:
                self.__children_removed.append(widget)
            self.children.remove(widget)
            widget._candy__parent = None
        self._queue_rendering()
        self._queue_sync_properties('children')
        
    def _candy_calculate_dynamic_size(self, size=None):
        """
        Adjust dynamic change to parent size changes. This function
        returns True if the size changed. If size is given, this will
        be used as parent size (needed for passive widgets).
        """
        if not super(Group, self)._candy_calculate_dynamic_size(size):
            # the size of the widget did not change, no need to update
            # the children of this group
            return False
        # update all non-passive children. The passive ones will be calculated
        # after all others are rendered
        for child in self.children:
            if not child.passive and child._dynamic_size:
                child._candy_calculate_dynamic_size()
        return True

    def _candy_prepare(self):
        """
        Prepare rendering
        """
        super(Group, self)._candy_prepare()
        # sync children
        for child in self.children:
            if child._sync_rendering:
                child._candy_prepare()

    def _clutter_render(self):
        """
        Render the widget
        """
        # reset clutter_size information
        self._intrinsic_size = None
        calculate_dynamic_size = 'size' in self._sync_properties
        if self._obj is None:
            self._obj = backend.Group()
            self._obj.show()
            calculate_dynamic_size = True
        # prepare new children
        while self.__children_added:
            self.__children_added.pop(0)._sync_properties['parent'] = self._obj
        # get a list of passive and not-passive children
        children = { True: [], False: [] }
        for child in self.children:
            children[child.passive].append(child)
        # render all non-passive children
        for child in children[False]:
            # calculate_dynamic_size and render non passive child
            if calculate_dynamic_size and child._dynamic_size:
                child._candy_calculate_dynamic_size()
            # render non-passive child
            if child._sync_rendering:
                child._sync_rendering = False
                child._clutter_render()
            # require layout when a child changes layout
            self._sync_layout = self._sync_layout or child._sync_layout
        # check if we have passive children that require rendering or layout
        while not self._sync_layout and children[True]:
            child = children[True].pop()
            self._sync_layout = child._sync_layout or child._sync_rendering
        return children[False]

    def _clutter_sync_layout(self):
        """
        Layout the widget
        """
        # sync non-passive children and remember the passive ones for later
        children = { True: [], False: [] }
        for child in self.children:
            children[child.passive].append(child)
        # sync group object
        super(Group,self)._clutter_sync_layout()
        # render and sync the layout of all passive children
        for child in children[False]:
            if child._sync_layout:
                child._sync_layout = False
                child._clutter_sync_layout()
        if not children[True]:
            # no passive children, we are done here
            return
        # render and sync the layout of all passive children
        width, height = self.intrinsic_size
        for child in children[True]:
            child._candy_calculate_dynamic_size((width, height))
            if child._sync_rendering:
                child._sync_rendering = False
                child._clutter_render()
            if child._sync_layout:
                child._sync_layout = False
                child._clutter_sync_layout()

    def _clutter_sync_properties(self):
        """
        Set some properties
        """
        if not super(Group, self)._clutter_sync_properties():
            # object destroyed
            return False
        # sync children
        for child in self.children:
            if child._sync_properties:
                child._clutter_sync_properties()
                child._sync_properties = {}
        # sync removed children
        while self.__children_removed:
            self._sync_layout = True
            child = self.__children_removed.pop(0)
            if child.parent is None:
                child._sync_properties['parent'] = None
                child._clutter_sync_properties()
        # restack children
        while self.__children_restack:
            child, direction = self.__children_restack.pop(0)
            if direction == 'top':
                child._obj.raise_top()
            if direction == 'bottom':
                child._obj.lower_bottom()
        return True

    @property
    def intrinsic_size(self):
        if not self._intrinsic_size:
            width = height = 0
            for child in self.children:
                if not child.passive:
                    width = max(width, child.x + child.width)
                    height = max(height, child.y + child.height)
            self._intrinsic_size = width, height
        return self._intrinsic_size

    def _candy_child_restack(self, child, direction):
        """
        Restack a child

        @param child: child widget
        @param direction: top or bottom
        """
        self.__children_restack.append((child, direction))
        self._queue_sync_properties('children')


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
    __spacing = 0
    __layout = None
    possible_layouts = {}

    def __init__(self, pos=None, size=None, layout=None, context=None):
        super(LayoutGroup, self).__init__(pos, size, context)
        if layout is not None:
            self.layout = layout

    @property
    def spacing(self):
        return self.__spacing

    @spacing.setter
    def spacing(self, spacing):
        self.__spacing = spacing
        self._queue_sync_layout()

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
        self._queue_sync_layout()

    def _clutter_render(self):
        """
        Render the widget
        """
        children = super(LayoutGroup, self)._clutter_render()
        if self.__layout:
            self.__layout(children, self.spacing)

    @classmethod
    def register_layout(cls, name, func):
        """
        Register a layout function to kaa.candy
        """
        cls.possible_layouts[name] = func


def layout_vertical(widgets, spacing):
    """
    Simple layout function to sort the widgets vertical
    """
    y = 0
    for widget in widgets:
        widget.y = y
        # FIXME: handle widget.height == 0
        y += widget.height + spacing

def layout_horizontal(widgets, spacing):
    """
    Simple layout function to sort the widgets horizontal
    """
    x = 0
    for widget in widgets:
        widget.x = x
        # FIXME: handle widget.width == 0
        x += widget.width + spacing

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
        @param dependency: list of context dependencies
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
                self.add(widget)
            except:
                log.exception('render')
        if dependency:
            for var in dependency:
                self.add_dependency(var)

    def get_widget(self, name):
        """
        Get child element with the given name. For group children this
        function will search recursive.

        @param name: name of the child
        @returns: widget or None
        """
        for child in self.children:
            if child.userdata.get('context:replace'):
                continue
            if child.name == name:
                return child
            if isinstance(child, Group):
                result = child.get_widget(name)
                if result is not None:
                    return result
        return None

    def _candy_context_prepare(self, context):
        """
        Try if the widget is capable of handling the context. This does not
        modify any internal variables and is thread safe.

        @param context: context dict
        """
        if not super(Container, self)._candy_context_prepare(context):
            return False
        for child in self.children[:]:
            if not child.context_sensitive or child._candy_context_prepare(context) or \
                   child.userdata.get('context:replace'):
                continue
            try:
                template = child.userdata.get('container:template')
                if not template:
                    # this only works for items based on templates
                    log.warning('unable to replace child %s', child)
                    continue
                replace = template(context)
                replace.prepare(self)
                replace.userdata['container:template'] = template
                child.userdata['context:replace'] = replace
            except:
                log.exception('render')
        return True

    def _candy_context_sync(self, context):
        """
        Set a new context for the container and redraw it.

        @param context: context dict
        """
        super(Container, self)._candy_context_sync(context)
        for child in self.children[:]:
            replace = child.userdata.get('context:replace')
            if replace:
                if replace is not True:
                    self._candy_replace_child(child, replace, context)
                    child.userdata['context:replace'] = True
                continue
            if child.context_sensitive:
                child._candy_context_sync(context)

    def _candy_replace_child(self, child, replace, context):
        """
        Replace child with a new one. This function is a callback from
        _candy_context_sync in case the container wants to add some animations.
        """
        async = []
        eventhandler = child.eventhandler.get('hide')
        if eventhandler:
            async.extend([ x(child, context) for x in eventhandler])
        self.add(replace)
        eventhandler = replace.eventhandler.get('show')
        if eventhandler is not None:
            async.extend([ x(replace, context) for x in eventhandler])
        if async:
            i = kaa.InProgressAll(*async)
            i.connect(self.__unparent_child, child, i)
        else:
            child.unparent()
        replace._sync_properties['stack-position'] = child

    def __unparent_child(self, result, child, ref):
        self.remove(child)

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
