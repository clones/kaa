# -*- coding: iso-8859-1 -*-
# -----------------------------------------------------------------------------
# factory.py
# -----------------------------------------------------------------------------
# $Id$
#
# -----------------------------------------------------------------------------
# kaa-Metadata - Media Metadata for Python
# Copyright (C) 2003-2006 Thomas Schueppel, Dirk Meyer
#
# First Edition: Thomas Schueppel <stain@acm.org>
# Maintainer:    Dirk Meyer <dischi@freevo.org>
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
#
# -----------------------------------------------------------------------------

__all__ = [ 'Factory', 'register', 'gettype', 'parse' ]

# python imports
import stat
import os
import sys
import urlparse
import traceback
import urllib
import logging

# kaa.metadata imports
import core

# get logging object
log = logging.getLogger('metadata')

# factory object
_factory = None

# some timing debug
TIME_DEBUG = False

R_MIMETYPE  = 0
R_EXTENTION = 1
R_CLASS     = 2

def Factory():
    """
    Create or return global unique factory object.
    """
    global _factory

    # One-time init
    if _factory == None:
        _factory = _Factory()
        _factory.import_parser()
    return _factory


def register(mimetype, extensions, c):
    """
    Register a parser to the factory.
    """
    return Factory().register(mimetype, extensions, c)


def gettype(mimetype, extensions):
    """
    Return parser for mimetype / extensions
    """
    return Factory().get(mimetype,extensions)


def parse(filename, force=True):
    """
    parse a file
    """
    result = Factory().create(filename, force)
    if result:
        result._finalize()
    return result


class _Factory:
    """
    Abstract Factory for the creation of Media instances. The different
    Methods create Media objects by parsing the given medium.
    """
    def __init__(self):
        self.extmap = {}
        self.mimemap = {}
        self.types = []
        self.device_types = []
        self.directory_types = []
        self.stream_types = []


    def import_parser(self):
        """
        This functions imports all known parser.
        """
        import audio.ogg
        import audio.m4a
        import audio.ac3
        import audio.pcm
        import audio.adts
        import video.riff
        import video.mpeg
        import video.asf
        import video.mov
        import video.flv
        import image.jpg
        import image.png
        import image.tiff
        import image.bmp
        import image.gif
        import video.vcd
        import video.real
        import video.ogm
        import video.mkv
        import misc.xml

        import disc.vcd
        import disc.audio
        import disc.dvd
        import disc.data

        import audio.mp3
        import audio.webradio
        import audio.flac

        import games.gameboy
        import games.snes

        import misc.directory


    def create_from_file(self, file, force=True):
        """
        create based on the file stream 'file
        """
        # Check extension as a hint
        e = os.path.splitext(file.name)[1].lower()
        parser = None
        if e and e.startswith('.') and e[1:] in self.extmap:
            log.debug("trying ext %s" % e[1:])
            file.seek(0,0)
            try:
                parser = self.extmap[e[1:]][R_CLASS]
                return parser(file)
            except core.ParseError:
                pass
            except (KeyboardInterrupt, SystemExit):
                sys.exit(0)
            except:
                log.exception('parse error')

        if not force:
            log.info('No Type found by Extension. Give up')
            return None

        log.info('No Type found by Extension. Trying all')

        for e in self.types:
            if e[R_CLASS] == parser:
                # We already tried this parser, don't bother again.
                continue
            log.debug('trying %s' % e[R_MIMETYPE])
            file.seek(0,0)
            try:
                return e[R_CLASS](file)
            except (KeyboardInterrupt, SystemExit):
                sys.exit(0)
            except:
                pass
        return None


    def create_from_url(self, url, force=True):
        """
        Create information for urls. This includes file:// and cd://
        """
        split  = urlparse.urlsplit(url)
        scheme = split[0]

        if scheme == 'file':
            (scheme, location, path, query, fragment) = split
            return self.create_from_filename(location+path, force)

        elif scheme == 'cdda':
            r = self.create_from_filename(split[4], force)
            if r:
                r.url = url
            return r

        elif scheme == 'http':
            # Quick Hack for webradio support
            # We will need some more soffisticated and generic construction
            # method for this. Perhaps move file.open stuff into __init__
            # instead of doing it here...
            for e in self.stream_types:
                log.debug('Trying %s' % e[R_MIMETYPE])
                try:
                    return e[R_CLASS](url)
                except core.ParseError:
                    pass
                except (KeyboardInterrupt, SystemExit):
                    sys.exit(0)

        elif scheme == 'dvd':
            path = split[2]
            if not path.replace('/', ''):
                return self.create_from_device('/dev/dvd')
            return self.create_from_filename(split[2])

        else:
            (scheme, location, path, query, fragment) = split
            uhandle = urllib.urlopen(url)
            mime = uhandle.info().gettype()
            log.debug("Trying %s" % mime)
            if self.mimemap.has_key(mime):
                try:
                    return self.mimemap[mime][R_CLASS](file)
                except core.ParseError:
                    pass
                except (KeyboardInterrupt, SystemExit):
                    sys.exit(0)
            # XXX Todo: Try other types
        pass


    def create_from_filename(self, filename, force=True):
        """
        Create information for the given filename
        """
        if os.path.isdir(filename):
            return None
        if os.path.isfile(filename):
            try:
                f = open(filename,'rb')
            except (IOError, OSError), e:
                log.info('error reading %s: %s' % (filename, e))
                return None
            except (KeyboardInterrupt, SystemExit):
                sys.exit(0)
            r = self.create_from_file(f, force)
            f.close()
            if r:
                r.url = 'file://%s' % os.path.abspath(filename)
                return r
        return None


    def create_from_device(self,devicename):
        """
        Create information from the device. Currently only rom drives
        are supported.
        """
        for e in self.device_types:
            log.debug('Trying %s' % e[R_MIMETYPE])
            try:
                t = e[R_CLASS](devicename)
                t.url = 'file://%s' % os.path.abspath(devicename)
                return t
            except core.ParseError:
                pass
            except (KeyboardInterrupt, SystemExit):
                sys.exit(0)
        return None


    def create_from_directory(self, dirname):
        """
        Create information from the directory.
        """
        for e in self.directory_types:
            log.debug('Trying %s' % e[R_MIMETYPE])
            try:
                return e[R_CLASS](dirname)
            except core.ParseError:
                pass
            except (KeyboardInterrupt, SystemExit):
                sys.exit(0)
        return None


    def create(self, name, force=True):
        """
        Global 'create' function. This function calls the different
        'create_from_'-functions.
        """
        try:
            if name.find('://') > 0:
                return self.create_from_url(name)
            if not os.path.exists(name):
                return None
            if (os.uname()[0] == 'FreeBSD' and \
                stat.S_ISCHR(os.stat(name)[stat.ST_MODE])) \
                or stat.S_ISBLK(os.stat(name)[stat.ST_MODE]):
                return self.create_from_device(name)
            if os.path.isdir(name):
                return self.create_from_directory(name)
            return self.create_from_filename(name, force)
        except (KeyboardInterrupt, SystemExit):
            sys.exit(0)
        except:
            log.exception('kaa.metadata.create error')
            log.warning('Please report this bug to the Freevo mailing list')
            return None



    def register(self, mimetype, extensions, c):
        """
        register the parser to kaa.metadata
        """
        log.debug('%s registered' % mimetype)
        tuple = (mimetype, extensions, c)

        if extensions == core.EXTENSION_DEVICE:
            self.device_types.append(tuple)
        elif extensions == core.EXTENSION_DIRECTORY:
            self.directory_types.append(tuple)
        elif extensions == core.EXTENSION_STREAM:
            self.stream_types.append(tuple)
        else:
            self.types.append(tuple)
            for e in extensions:
                self.extmap[e.lower()] = tuple
            self.mimemap[mimetype] = tuple


    def get(self, mimetype, extensions):
        """
        return the object for mimetype/extensions or None
        """
        if extensions == core.EXTENSION_DEVICE:
            l = self.device_types
        elif extensions == core.EXTENSION_DIRECTORY:
            l = self.directory_types
        elif extensions == core.EXTENSION_STREAM:
            l = self.stream_types
        else:
            l = self.types

        for info in l:
            if info[R_MIMETYPE] == mimetype and info[R_EXTENSION] == extensions:
                return info[R_CLASS]
        return None
