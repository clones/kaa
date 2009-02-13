# -*- coding: iso-8859-1 -*-
# -----------------------------------------------------------------------------
# error.py - Exceptions used by kaa.xmpp
# -----------------------------------------------------------------------------
# $Id$
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

class XMPPException(Exception):
    """
    Exception raised on IQ error results.
    """
    def __init__(self, error):
        Exception.__init__(self, str(error))
        self.error = self.code = None
        if not isinstance(error, str):
            self.error = error
            self.code = int(error.get('code', 0))

    def __str__(self):
        return Exception.__str__(self)

class XMPPTracebackError(XMPPException):
    """
    Exception raised on IQ error results.
    """
    def __init__(self, error):
        trace = str(error.get_child('trace').content)
        XMPPException.__init__(self, trace)
        self.error = error
        self.code = int(error.get('code', 0))
        self.formatted_traceback = trace

class CancelException(XMPPException):
    pass

class XMPPRecipientUnavailableError(XMPPException):
    pass

class XMPPNotImplementedError(XMPPException):
    pass

class XMPPStreamError(XMPPException):
    pass

class XMPPConnectError(Exception):
    pass
