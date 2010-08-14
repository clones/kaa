# -*- coding: iso-8859-1 -*-
# $Id$
# -----------------------------------------------------------------------------
# utils.py - mplayer backend utility functions
# -----------------------------------------------------------------------------
# kaa.popcorn - Generic Player API
# Copyright (C) 2008 Jason Tackaberry, Dirk Meyer
#
# Please see the file AUTHORS for a complete list of authors.
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
# -----------------------------------------------------------------------------

__all__ = [ 'ArgumentList', 'get_mplayer_info' ]

# python imports
import re
import os
import stat

# kaa imports
import kaa

# A cache holding values specific to an MPlayer executable (version,
# filter list, video/audio driver list, input keylist).  This dict is
# keyed on the full path of the MPlayer binary.
_cache = {}


class ArgumentList(list):
    """
    Argument list.
    """
    def __init__(self, args=()):
        if isinstance(args, basestring):
            args = args.split(' ')
        list.__init__(self, args)

    def __getslice__(self, i, j):
        return ArgumentList(list.__getslice__(self, i, j))

    def add(self, **kwargs):
        """
        Add -key=value arguments.
        """
        for key, value in kwargs.items():
            opt = '-' + key.replace('_', '-')
            if value is True:
                self.append(opt)
            else:
                self.extend((opt, str(value)))

    def extend(self, arg):
        try:
            list.extend(self, arg.split(' '))
        except AttributeError:
            list.extend(self, arg)


def get_mplayer_info(path):
    """
    Fetches info about the given MPlayer executable.  This function returns a
    dictionary containing supported features of MPlayer.  A cache is
    maintained, so subsequent invocations of this function are less expensive.
    """
    try:
        # Fetch the mtime of the binary
        mtime = os.stat(path)[stat.ST_MTIME]
    except (OSError, TypeError):
        return None

    if path in _cache and _cache[path]["mtime"] == mtime:
        # Cache isn't stale, so return that.
        return _cache[path]

    info = {
        "version": None,
        "mtime": mtime,
        "video_filters": {},
        "video_drivers": {},
        "video_codecs": {},
        "audio_filters": {},
        "audio_drivers": {},
        "audio_codecs": {},
        "keylist": [],
        "max_channels": 6,
    }

    groups = {
        'video_filters': ('Available video filters', r'\s*(\w+)\s+:\s+(.*)'),
        'video_drivers': ('Available video output', r'\s*(\w+)\s+(.*)'),
        'video_codecs': ('Available video codecs', r'\s*(\w+)\s+(\S+)\s+(\S+)\s+(.*)'),
        'audio_filters': ('Available audio filters', r'\s*(\w+)\s+:\s+(.*)'),
        'audio_drivers': ('Available audio output', r'\s*(\w+)\s+(.*)'),
        'audio_codecs': ('Available audio codecs', r'\s*(\w+)\s+(\S+)\s+(\S+)\s+(.*)'),
    }

    curgroup = None
    for line in os.popen('%s -vf help -af help -vo help -ao help -vc help -ac help 2>/dev/null' % path):
        # Check version
        if line.startswith("MPlayer "):
            info['version'] = line.split()[1]
        # Find current group.
        for group, (header, regexp) in groups.items():
            if line.startswith(header):
                curgroup = group
                break
        if not curgroup:
            continue

        # Check regexp
        m = re.match(groups[curgroup][1], line.strip())
        if not m:
            continue

        if len(m.groups()) > 2:
            info[curgroup][m.group(1)] = m.groups()[1:]
        elif len(m.groups()) == 2:
            info[curgroup][m.group(1)] = m.group(2)
        else:
            info[curgroup].append(m.group(1))

    # Another pass for key list.
    for line in os.popen('%s -input keylist 2>/dev/null' % path):
        # Check regexp
        m = re.match(r'^(\w+)$', line.strip())
        if not m:
            continue
        info['keylist'].append(m.group(1))

    # Detect 6 or 8 channel audio based on MPlayer version.  We could call it
    # again with -channels 8 and check the exit code, but we've already called
    # it twice and the overhead for each call is high.
    m = re.search(r'-(r|svn)(\d{5,})', info['version'])
    if m:
        # 8 channel audio support added to r29868 (2009-11-10).
        prefix, ver = m.group(1), int(m.group(2)) if m.group(2).isdigit() else 0
        if (prefix == 'r' and ver >= 29868) or (prefix == 'svn' and ver >= 20091110):
            info['max_channels'] = 8
    elif info['version'] >= '1.0rc3':
        # Available in 1.0rc3 or later.
        info['max_channels'] = 8
           
    _cache[path] = info
    return info
