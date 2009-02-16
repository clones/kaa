# -*- coding: iso-8859-1 -*-
# -----------------------------------------------------------------------------
# api.py - kaa.xmpp public API
# -----------------------------------------------------------------------------
# $Id$
#
# This file is needed to make it possible for extensions to import the
# xmpp API without importing kaa.xmp with the full path.
#
# -----------------------------------------------------------------------------
# kaa.xmpp - XMPP framework for the Kaa Media Repository
# Copyright (C) 2008 Dirk Meyer
#
# First Edition: Dirk Meyer <dischi@freevo.org>
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
import string
import random

from client import Client
from remote import RemoteNode
from element import Element, Message, IQ, Result, Error
from feature import Feature
from parser import stanza, message, iq
from error import *
from plugin import ClientPlugin, RemotePlugin, add_extension
import stream
import config

def create_id():
    return ''.join([random.choice(string.letters + string.digits) for i in range(8)])
