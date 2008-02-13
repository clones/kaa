# -*- coding: iso-8859-1 -*-
# -----------------------------------------------------------------------------
# httpreader.py - wrapper for urllib
# -----------------------------------------------------------------------------
# $Id$
#
# -----------------------------------------------------------------------------
# kaa-webinfo - Python module for gathering information from the web
# Copyright (C) 2002-2005 Viggo Fredriksen, Dirk Meyer, et al.
#
# First Edition: Dirk Meyer <dischi@freevo.org>
# Maintainer:    Dirk Meyer <dischi@freevo.org>
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

import urllib
import sys
import cStringIO

from kaa.notifier import Signal, MainThreadCallback, Thread, IOMonitor
import kaa.notifier

class HTTPReader(urllib.FancyURLopener):
    def __init__(self, header={}, username=None, password=None):
        urllib.FancyURLopener.__init__(self)
        self.signals = {'headers'   : Signal(),
                        'exception' : Signal(),
                        'status'    : Signal(),
                        'progress'  : Signal(),
                        'completed' : Signal() }

        self.headers = {   
            'User-Agent': 'kaa-webinfo %s (%s)' % (1, sys.platform),
            'Accept-Language': 'en-US' }
        for key, value in header.items():
            self.headers[key] = value
        self._user_passwd = username, password
        self._last_user_passwd = username, password
        self.show_progress = True
        self.running = False

        self.status_callback = MainThreadCallback(self.signals['status'].emit)
        


    def get_user_passwd(self, *args, **kwargs):
        self._last_user_passwd = self._user_passwd
        self._user_passwd = None, None
        return self._last_user_passwd

    
    def get(self, url, fname = None):
        if self.running:
            raise IOError('HTTPReader already active')
        
        t = Thread(self._get, url, fname).start()
        self.running = True


    def active(self):
        return self.running

    
    def _get(self, url, fname):
        if fname:
            output = open(fname, 'w')
        else:
            output = cStringIO.StringIO()
        stream = self.open(url)
        MainThreadCallback(self.signals['headers'].emit)(stream.headers)
        self.progress_callback = None
        length = 0
        if self.signals['progress'].count() > 0:
            self.progress_callback = MainThreadCallback(self.signals['progress'].emit)
        try:
            length = int(stream.headers['content-length'])
        except (KeyError, ValueError):
            pass

        self._user_passwd = self._last_user_passwd

        while 1:
            buf = stream.read(16*1024)
            if not buf:
                break
            if not kaa.notifier.running:
                output.close()
                return
            output.write(buf)
            if self.progress_callback and self.show_progress:
                self.progress_callback(output.tell(), length)
        if fname:
            output.close()
            MainThreadCallback(self.signals['completed'].emit)()
        else:
            output.seek(0)
            try:
                result = self._handle_result_threaded(output)
            except Exception, e:
                MainThreadCallback(self.signals['exception'].emit)(e.__class__, e, sys.exc_traceback)
            else:
                MainThreadCallback(self._finished, result)()
        self.running = False
        return False

    def _finished(self, result):
        result = self._handle_result(result)
        self.signals['completed'].emit(result)

    def _handle_result(self, output):
        return output

    def _handle_result_threaded(self, output):
        return output
        
