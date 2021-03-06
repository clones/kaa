# -*- coding: iso-8859-1 -*-
# -----------------------------------------------------------------------------
# logger.py - Updates to the Python logging module
# -----------------------------------------------------------------------------
# $Id$
#
# This module 'fixes' the Python logging module to accept fixed string and
# unicode arguments. It will also make sure that there is a logging handler
# defined when needed.
#
# -----------------------------------------------------------------------------
# Copyright 2006-2009 Dirk Meyer, Jason Tackaberry
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
from __future__ import absolute_import

# Python imports
import logging
import sys

# kaa.base imports
if sys.hexversion >= 0x02060000:
    # Python 2.6 and 3.1's logger does the right thing with Unicode.  Actually,
    # Python 2.6.2 is broken if you pass it an encoded string (it tries to call
    # encode() on it before writing to the stream).  This problem is fixed with
    # at least 2.6.5, but either version behaves sanely if you give it unicode
    # strings.
    from .strutils import py3_str as logger_str_convert
else:
    # On the other hand, Python 2.5's logging module is less robust with unicode,
    # so convert arguments to non-unicode strings.
    from .strutils import py3_b as logger_str_convert


def create_logger(level = logging.WARNING):
    """
    Create a simple logging object for applicatins that don't want
    to create a logging handler on their own. You should always have
    a logging object.
    """
    log = logging.getLogger()
    # delete current handler
    for l in log.handlers:
        log.removeHandler(l)

    # Create a simple logger object
    if len(logging.getLogger().handlers) > 0:
        # there is already a logger, skipping
        return

    formatter = logging.Formatter('%(asctime)s [%(levelname)s] %(module)s(%(lineno)s): %(message)s')
    handler = logging.StreamHandler()
    handler.setFormatter(formatter)
    log.addHandler(handler)


_makeRecord = logging.Logger.makeRecord

def make_record(self, name, level, fn, lno, msg, args, *_args, **_kwargs):
    """
    A special makeRecord class for the logger to convert msg and args into
    strings using the correct encoding if they are unicode strings. This
    function also makes sure we have at least a basic handler.
    """
    if len(self.root.handlers) == 0:
        # create handler, we don't have one
        create_logger()

    # ensure msg and args are unicode (python 2.6+) or non-unicode (python 2.5)
    msg = logger_str_convert(msg)
    args = tuple(logger_str_convert(x) for x in args)
    # Allow caller to override default location by specifying a 2-tuple
    # (filename, lineno) as 'location' in the extra dict.
    extra = _args[2]
    if extra and 'location' in extra:
        fn, lno = extra['location']

    # call original function
    return _makeRecord(self, name, level, fn, lno, msg, args, *_args, **_kwargs)


# override makeRecord of a logger by our new function that can handle
# unicode correctly and that will take care of a basic logger.
logging.Logger.makeRecord = make_record


# Replace logger class with a custom logger that implements a debug2() method,
# using a new DEBUG2 log level.
class Logger(logging.Logger):
    def debug2(self, msg, *args, **kwargs):
        if self.manager.disable >= logging.DEBUG2:
            return
        if logging.DEBUG2 >= self.getEffectiveLevel():
            apply(self._log, (logging.DEBUG2, msg, args), kwargs)

logging.DEBUG2 = 5
logging.addLevelName(logging.DEBUG2, 'DEBUG2')
logging.setLoggerClass(Logger)
