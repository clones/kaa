# -*- coding: iso-8859-1 -*-
# -----------------------------------------------------------------------------
# xmltv.py - xmltv parser
# -----------------------------------------------------------------------------
# $Id$
#
# This file is based on the xmltv parser by James Oakley. Most of it is still
# his work. We did the following changes for kaa.epg:
#
#  o change data_format to '%Y%m%d%H%M%S %Z'
#  o delete all encode, return Unicode
#  o add except AttributeError: for unhandled elements
#  o delete writer
#  o add read function to read everything
#
# Notes from James in the original file:
#
#  o Uses qp_xml instead of DOM. It's way faster
#  o Read and write functions use file objects instead of filenames
#  o Unicode is removed on dictionary keys because the xmlrpclib marshaller
#    chokes on it. It'll always be Latin-1 anyway... (famous last words)
#
#  Yes, A lot of this is quite different than the Perl module, mainly to keep
#  it Pythonic
#
# -----------------------------------------------------------------------------
# kaa-epg - Python EPG module
# Copyright (C) 2001-2005 Dirk Meyer, Rob Shortt, et al.
#
# First Edition: James Oakley <jfunk@funktronics.ca>
# Maintainer:    Dirk Meyer <dmeyer@tzi.de>
#
# Please see the file doc/AUTHORS for a complete list of authors.
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

__all__ = ['parse' ]

# python imports
from xml.utils import qp_xml
from xml.sax import saxutils
import string, types, re

# The Python-XMLTV version
VERSION = "0.5.15"

# The date format used in XMLTV
date_format = '%Y%m%d%H%M%S %Z'

# Note: Upstream xmltv.py uses %z so remember to change that when syncing
date_format_notz = '%Y%m%d%H%M%S'

# These characters are illegal in XML
_chars = u'[^\x09\x0A\x0D\x20-\uD7FF\uE000-\uFFFD\u10000-\u10FFFF]'
XML_BADCHARS = re.compile(_chars)


#
# Options. They may be overridden after this module is imported
#

# The extraction process could be simpler, building a tree recursively
# without caring about the element names, but it's done this way to allow
# special handling for certain elements. If 'desc' changed one day then
# ProgrammeHandler.desc() can be modified to reflect it

class _ProgrammeHandler(object):
    """
    Handles XMLTV programme elements
    """

    #
    # <tv> sub-tags
    #

    def title(self, node):
        return _readwithlang(node)

    def sub_title(self, node):
        return _readwithlang(node)

    def desc(self, node):
        return _readwithlang(node)

    def credits(self, node):
        return _extractNodes(node, self)

    def date(self, node):
        return node.textof()

    def category(self, node):
        return _readwithlang(node)

    def language(self, node):
        return _readwithlang(node)

    def orig_language(self, node):
        return _readwithlang(node)

    def length(self, node):
        data = {}
        data['units'] = _getxmlattr(node, u'units')
        try:
            length = int(node.textof())
        except ValueError:
            pass
        data['length'] = length
        return data

    def icon(self, node):
        data = {}
        for attr in (u'src', u'width', u'height'):
            if node.attrs.has_key(('', attr)):
                data[attr] = _getxmlattr(node, attr)
        return data

    def url(self, node):
        return node.textof()

    def country(self, node):
        return _readwithlang(node)

    def episode_num(self, node):
        system = _getxmlattr(node, u'system')
        if system == '':
            system = 'onscreen'
        return (node.textof(), system)

    def video(self, node):
        result = {}
        for child in node.children:
            result[child.name] = self._call(child)
        return result

    def audio(self, node):
        result = {}
        for child in node.children:
            result[child.name] = self._call(child)
        return result

    def previously_shown(self, node):
        data = {}
        for attr in (u'start', u'channel'):
            if node.attrs.has_key(('', attr)):
                data[attr] = node.attrs[('', attr)]
        return data

    def premiere(self, node):
        return _readwithlang(node)

    def last_chance(self, node):
        return _readwithlang(node)

    def new(self, node):
        return 1

    def subtitles(self, node):
        data = {}
        if node.attrs.has_key(('', u'type')):
            data['type'] = _getxmlattr(node, u'type')
        for child in node.children:
            if child.name == u'language':
                data['language'] = _readwithlang(child)
        return data

    def rating(self, node):
        data = {}
        data['icon'] = []
        if node.attrs.has_key(('', u'system')):
            data['system'] = node.attrs[('', u'system')]
        for child in node.children:
            if child.name == u'value':
                data['value'] = child.textof()
            elif child.name == u'icon':
                data['icon'].append(self.icon(child))
        if len(data['icon']) == 0:
            del data['icon']
        return data

    def star_rating(self, node):
        data = {}
        data['icon'] = []
        for child in node.children:
            if child.name == u'value':
                data['value'] = child.textof()
            elif child.name == u'icon':
                data['icon'].append(self.icon(child))
        if len(data['icon']) == 0:
            del data['icon']
        return data


    #
    # <credits> sub-tags
    #

    def actor(self, node):
        return node.textof()

    def director(self, node):
        return node.textof()

    def writer(self, node):
        return node.textof()

    def adapter(self, node):
        return node.textof()

    def producer(self, node):
        return node.textof()

    def presenter(self, node):
        return node.textof()

    def commentator(self, node):
        return node.textof()

    def guest(self, node):
        return node.textof()


    #
    # <video> and <audio> sub-tags
    #

    def present(self, node):
        return _decodeboolean(node)

    def colour(self, node):
        return _decodeboolean(node)

    def aspect(self, node):
        return node.textof()

    def stereo(self, node):
        return node.textof()


    #
    # Magic
    #

    def _call(self, node):
        try:
            return getattr(self, string.replace(node.name, '-', '_'))(node)
        except NameError:
            return '**Unhandled Element**'
        except AttributeError:
            return '**Unhandled Element**'

class _ChannelHandler(object):
    """
    Handles XMLTV channel elements
    """
    def display_name(self, node):
        return _readwithlang(node)

    def icon(self, node):
        data = {}
        for attr in (u'src', u'width', u'height'):
            if node.attrs.has_key(('', attr)):
                data[attr] = _getxmlattr(node, attr)
        return data

    def url(self, node):
        return node.textof()


    #
    # More Magic
    #

    def _call(self, node):
        try:
            return getattr(self, string.replace(node.name, '-', '_'))(node)
        except NameError:
            return '**Unhandled Element**'


#
# Some convenience functions, treat them as private
#

def _extractNodes(node, handler):
    """
    Builds a dictionary from the sub-elements of node.
    'handler' should be an instance of a handler class
    """
    result = {}
    for child in node.children:
        if not result.has_key(child.name):
            result[child.name] = []
        result[child.name].append(handler._call(child))
    return result


def _getxmlattr(node, attr):
    """
    If 'attr' is present in 'node', return the value, else return an empty
    string

    Yeah, yeah, namespaces are ignored and all that stuff
    """
    if node.attrs.has_key((u'', attr)):
        return node.attrs[(u'', attr)]
    else:
        return u''


def _readwithlang(node):
    """
    Returns a tuple containing the text of a 'node' and the text of the 'lang'
    attribute
    """
    return (node.textof(), _getxmlattr(node, u'lang'))


def _decodeboolean(node):
    text = node.textof().lower()
    if text == 'yes':
        return 1
    elif text == 'no':
        return 0
    else:
        return None


def _node_to_programme(node):
    """
    Create a programme dictionary from a qp_xml 'node'
    """
    handler = _ProgrammeHandler()
    programme = _extractNodes(node, handler)

    for attr in (u'start', u'channel'):
        programme[attr] = node.attrs[(u'', attr)]
    if (u'', u'stop') in node.attrs:
        programme[u'stop'] = node.attrs[(u'', u'stop')]
    #else:
        # Sigh. Make show zero-length. This will allow the show to appear in
        # searches, but it won't be seen in a grid, if the grid is drawn to
        # scale
        #programme[u'stop'] = node.attrs[(u'', u'start')]
    return programme


def _node_to_channel(node):
    """
    Create a channel dictionary from a qp_xml 'node'
    """
    handler = _ChannelHandler()
    channel = _extractNodes(node, handler)

    channel['id'] = node.attrs[('', 'id')]
    return channel


def parse(fp):
    """
    Read all data. The function will return a list a dict of additional data
    and a dict of channels with all the programmes.
    """
    parser = qp_xml.Parser()
    doc = parser.parse(fp.read())

    attrs = {}

    for key in doc.attrs.keys():
        attrs[key[1]] = doc.attrs[key]

    channels = {}

    for node in doc.children:
        if node.name == u'channel':
            c = _node_to_channel(node)
            c['programs'] = []
            channels[c['id']] = c
        if node.name == u'programme':
            p = _node_to_programme(node)
            channels[p['channel']]['programs'].append(p)
    return attrs, channels
