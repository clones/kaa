# -*- coding: iso-8859-1 -*-
# -----------------------------------------------------------------------------
# strutils.py - Miscellaneous utilities for string handling
# -----------------------------------------------------------------------------
# $Id$
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

__all__ = [
    'ENCODING', 'BYTES_TYPE', 'UNICODE_TYPE', 'get_encoding', 'set_encoding',
    'utf8', 'str_to_unicode', 'unicode_to_str', 'format', 'py3_b', 'py3_str'
]

# python imports
import sys
import locale
import imp

# find the correct encoding
try:
    ENCODING = locale.getdefaultlocale()[1]
    ''.encode(ENCODING)
except (UnicodeError, TypeError):
    ENCODING = 'latin-1'

if sys.hexversion >= 0x03000000:
    UNICODE_TYPE = str
    BYTES_TYPE = bytes
    long = int
else:
    bytes = lambda s, dummy: str(s)
    UNICODE_TYPE = unicode
    BYTES_TYPE = str


def get_encoding():
    """
    Return the current encoding.
    """
    return ENCODING


def set_encoding(encoding):
    """
    Set default character encoding. This function also sets the global Python
    encoding.
    """
    global ENCODING
    ENCODING = encoding
    try:
        # Set python's global encoding (kludge and only works for Python 2.x)
        reload(sys)
        sys.setdefaultencoding(encoding)
    except (NameError, ValueError):
        pass


def py3_b(value, encoding=None, desperate=True, coerce=False):
    """
    Convert (if necessary) the given value to a "string of bytes", agnostic to
    any character encoding.

    :param value: the value to be converted to a string of bytes
    :param encoding: the character set to first try to encode to; if None, will
                     use the system default (from the locale).
    :type encoding: str
    :param desperate: if True and encoding to the given (or default) charset
                      fails, will also try utf-8 and latin-1 (in that order),
                      and if those fail, will encode to the preferred charset,
                      replacing unknown characters with \\uFFFD.
    :type desperate: bool
    :param coerce: if True, will coerce numeric types to a bytes object; if
                   False, such values will be returned untouched.
    :type coerce: bool
    :returns: the value as a string of bytes, or the original value if coerce is
              False and the value was not a bytes or string.

    .. note:: The notion of "bytes" was introduced in Python 3 (and included
       in Python 2.6 as an alias to str), hence the ``py3_`` prefix.  On Python
       2, the returned value is a *str* object while on Python 3, the returned
       value is a *bytes* object.
    """
    if isinstance(value, BYTES_TYPE):
        # Nothing to do.
        return value
    elif not isinstance(value, UNICODE_TYPE):
        if not coerce and isinstance(value, (int, long, float)):
            return value
        # Need to coerce to a unicode before converting to bytes.  We can't just
        # feed it to bytes() in case the default character set can't encode it.
        value = py3_str(value)

    for c in (encoding or ENCODING, 'utf-8', 'latin-1'):
        try:
            return value.encode(c)
        except UnicodeError:
            pass
        if not desperate:
            raise UnicodeError("Couldn't encode value to bytes (and not desperate enough to keep trying)")

    return value.encode(encoding or ENCODING, 'replace')


def py3_str(value, encoding=None, desperate=True, coerce=False):
    """
    Convert (if necessary) the given value to a (unicode) string.

    :param value: the value to be converted to a unicode string
    :param encoding: the character set to first try to decode as; if None, will
                     use the system default (from the locale).
    :type encoding: str
    :param desperate: if True and decoding to the given (or default) charset
                      fails, will also try utf-8 and latin-1 (in that order),
                      and if those fail, will decode as the preferred charset,
                      replacing unknown characters with \\uFFFD.
    :type desperate: bool
    :param coerce: if True, will coerce numeric types to a unicode string; if
                   False, such values will be returned untouched.
    :type coerce: bool
    :returns: the value as a (unicode) string, or the original value if coerce is
              False and the value was not a bytes or string.

    .. note:: The naming of ``str`` is relative Python 3's notion of a *str* object,
       hence the ``py3_`` prefix.  On Python 2, the returned value is a *unicode*
       object while on Python 3, the returned value is a *str* object.
    """
    if isinstance(value, UNICODE_TYPE):
        # Nothing to do.
        return value
    elif not isinstance(value, BYTES_TYPE):
        if not coerce and isinstance(value, (int, long, float)):
            return value
        # Need to coerce this value.  Try the direct approach.
        try:
            return UNICODE_TYPE(value)
        except UnicodeError:
            # Could be that value.__repr__ returned a non-unicode and
            # non-8bit-clean string.  Be a bit more brute force about it.
            return py3_str(repr(value), desperate=desperate)

    # We now have a bytes object to decode.
    for c in (encoding or ENCODING, 'utf-8', 'latin-1'):
        try:
            return value.decode(c)
        except UnicodeError:
            pass
        if not desperate:
            raise UnicodeError("Couldn't decode value to unicode (and not desperate enough to keep trying)")

    return value.decode(encoding or ENCODING, 'replace')


def utf8(s):
    """
    Returns a UTF-8 string, converting from other character sets if
    necessary.
    """
    return py3_str(s).encode('utf-8')


def str_to_unicode(s, encoding=None):
    "This function is deprecated; use py3_str() instead."
    return py3_str(s, encoding)

def unicode_to_str(s, encoding=None):
    "This function is deprecated; use py3_b() instead."
    return py3_b(s, encoding)

def to_unicode(s, encoding=None):
    "This function is deprecated; use py3_str() instead."
    # (Nobody was using it anyway.)
    return py3_str(s, encoding, coerce=True)

def to_str(s, encoding=None):
    "This function is deprecated; use py3_b() instead."
    # Nobody was using it anyway.
    return py3_b(s, encoding, coerce=True)

def format(s, *args):
    """
    Format a string and make sure all string or unicode arguments are
    converted to the correct type.
    """
    if type(s) == BYTES_TYPE:
        return s % tuple(py3_b(x) for x in args)
    elif type(s) == UNICODE_TYPE:
        return s % tuple(py3_str(x) for x in args)
    else:
        raise TypeError('Format string must be str or unicode')
