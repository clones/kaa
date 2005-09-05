# -*- coding: iso-8859-1 -*-
# -----------------------------------------------------------------------------
# urlcache.py - module for caching results from a URL
# -----------------------------------------------------------------------------
# $Id$
#
# Notes:  This module contains some objects to make it simple to cache data
#     from a URL and save the results in any desired format.
#
#     URLCache:  The main cache object.  This is instantiated with a mandatory
#         argument cachefile and optional arguments hook_fetch and hook_parse.
#
#         cachefile:  The file conaining the cached data
#
#         hook_fetch:  If you have your own means to retrieving the URL you can
#             supply it here.  It must take a single argument for the URL.
#
#         hook_parse:  If you don't want to cache the complete results from the
#             URL use this hook to supply a method to parse the data.  For 
#             example you may only care about a few properties of the URL in
#             question so you could cache a custom object instead.
#
#     URLCacheItem:  Used internally by URLCache for each URL.  Each item has
#         a lifetime in which it will be expired.
#
# -----------------------------------------------------------------------------
# kaa-webinfo - Python module for gathering information from the web
# Copyright (C) 2002-2005 Rob Shortt, Dirk Meyer, et al.
#
# First Edition: Rob Shortt <rob@tvcentric.com>
# Maintainer:    Rob Shortt <rob@tvcentric.com>
#
# Please see the file doc/CREDITS for a complete list of authors.
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

import logging
import string
import time
import urllib

import os
import sys
import pickle
import cPickle


log = logging.getLogger('webinfo')

# TODO: Make the default cache interval random to avoid slowdowns if several
#       things are cached at the same time.
DEFAULT_CACHE_INTERVAL = 3600 * 5


# Pickle code from freevo.util.cache.  Maybe this should go into kaa.base.utils
# or something.
#
if float(sys.version[0:3]) < 2.3:
    PICKLE_PROTOCOL = 1
else:
    PICKLE_PROTOCOL = pickle.HIGHEST_PROTOCOL



def load(file, version=None):
    """
    Load a cache from disc. If version is given, the version field in the
    cachefile is checked and the function will return None if the field
    doesn't match. Notice: if a file is saved using a version field, this
    version must also be given on loading.
    """
    try:
        f = open(file, 'r')
        try:
            data = cPickle.load(f)
        except:
            data = pickle.load(f)
        f.close()
        if version and data[0] == version:
            return data[1]
        elif version == None:
            return data
        return None
    except:
        return None


def save(file, data, version=None):
    """
    Save the data to the given file. If version is given, this information will
    also be stored in the cachefile. Notice: when using a version here, the
    version parameter must also be used when loading the data again.
    """
    try:
        f = open(file, 'w')
    except (OSError, IOError):
        if os.path.isfile(file):
            os.unlink(file)
        try:
            f = open(file, 'w')
        except (OSError, IOError), e:
            try:
                os.makedirs(os.path.dirname(file))
                f = open(file, 'w')
            except (OSError, IOError), e:
                print 'cache.save: %s' % e
                return
    if version:
        cPickle.dump((version, data), f, PICKLE_PROTOCOL)
    else:
        cPickle.dump(data, f, PICKLE_PROTOCOL)
    f.close()



class URLCache(object):

    def __init__(self, cachefile, hook_fetch=None, hook_parse=None):
        self.cachefile = cachefile

        # items is what we cache in the pickle
        self.load_cache()

        if hook_fetch:
            self.hook_fetch = hook_fetch
        else:
            self.hook_fetch = self.default_hook_fetch

        if hook_parse:
            self.hook_parse = hook_parse
        else:
            self.hook_parse = self.default_hook_parse


    def get_item(self, URL):
        """
        returns an item or None if it failed
        """

        print 'get_item: 1'
        save = False
        item = self.items.get(URL)

        if item == None:
            item = URLCacheItem(URL)
            self.items[URL] = item

        if item.expired():
            save = True
            if not self.refresh_item(item):
                log.error('failed to refresh: %s' % item.URL)
                del(item)

        if save:
            self.save_cache()

        return self.items.get(URL)


    def get(self, URL):
        """
        returns the data stored in the item or None if there's a problem
        """

        print 'get: 1'
        item = self.get_item(URL)

        if item:
            return item.get()

        return None


    def refresh_item(self, item):
        try:
            rawstuff = self.hook_fetch(item.URL)
        except:
            log.error('failed to fetch: %s' % item.URL)
            return False

        try:
            stuff = self.hook_parse(rawstuff)
        except:
            log.error('failed to parse: %s' % item.URL)
            return False

        item.set(stuff)
        return True


    def default_hook_fetch(self, URL):
        # XXX: Should we wrap this in a thread?
        urlfile  = urllib.urlopen(URL)
        # XXX: What about Unicode?
        return string.join(urlfile.readlines(), '\n')
        

    def default_hook_parse(self, stuff):
        return stuff


    def save_cache(self):
        save(self.cachfile, self.items)


    def load_cache(self):
        cached_stuff = load(self.cachefile)
        if cached_stuff:
            self.items = cached_stuff
        else:
            self.items = {}



class URLCacheItem(object):

    def __init__(self, URL):
        print 'URLCacheItem::init: 1'
        self.URL = URL
        self._object = None
        self.cache_time = 0
        self.cache_interval = DEFAULT_CACHE_INTERVAL


    def set(self, stuff):
        self._object = stuff
        self.cache_time = time.time()


    def get(self):
        return self._object 


    def expired(self):
        if time.time() > self.cache_time + self.cache_interval:
            return True

        return False



