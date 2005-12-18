# -*- coding: iso-8859-1 -*-
# -----------------------------------------------------------------------------
# db_base.py - base for sqlite databases
# -----------------------------------------------------------------------------
# $Id$
#
# -----------------------------------------------------------------------------
# kaa-epg - Python EPG module
# Copyright (C) 2002-2005 Dirk Meyer, Rob Shortt, et al.
#
# First Edition: Dirk Meyer <dmeyer@tzi.de>
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

# python imports
import os
import logging

# kaa imports
import kaa.notifier

# epg imports
import schema

# get logging object
log = logging.getLogger('epg')

latest_version = "0.2"


class Database(object):
    """
    Database class for sqlite usage
    """
    def __init__(self, dbpath):
        """
        Create database and connect to it.
        """
        dbmissing = False
        try:
            # Check the database file
            if os.path.isfile(dbpath):
                if os.path.getsize(dbpath) == 0:
                    e = 'EPG database is zero size (invalid), removing it'
                    log.error(e)
                    os.unlink(dbpath)
            else:
                log.warning('EPG database missing, creating it')
                dbmissing = True

        except OSError, e:
            if os.path.isfile(dbpath):
                log.exception('Problem reading %s, check permissions' % dbpath)
            raise e

        self.open(dbpath)
        
        if not dbmissing:
            ver = self.get_version()
            log.debug('EPG database version %s' % ver)
            if ver != latest_version:
                warning = 'EPG database out of date, creating a new one, ' + \
                          'latest version is %s'
                log.warning(warning % latest_version)
                self.db.close()
                dbmissing = True
                os.unlink(dbpath)
                self.open(dbpath)
                
        if dbmissing:
            self.create()


    def create(self):
        """
        Create the db.
        """
        raise AttributeError('Not defined')

        
    def open(self, dbpath):
        """
        Open the db.
        """
        raise AttributeError('Not defined')


    def close(self):
        """
        Close database connection.
        """
        self.db.close()


    def execute(self, query):
        """
        Execute a query. The parameter as_list has no effect on this backend.
        """
        while 1:
            try:
                self.cursor.execute(Unicode(query))
                return self.cursor.fetchall()
            except self.OperationalError, e:
                # keep main loop alive
                kaa.notifier.step(False, False)


    def commit(self):
        """
        Execute a query. The parameter as_list has no effect on this backend.
        """
        while 1:
            try:
                self.db.commit()
                return
            except self.OperationalError, e:
                # keep main loop alive
                kaa.notifier.step(False, False)


    def get_version(self):
        """
        Get database version information.
        """
        if not self.execute('select name from sqlite_master where ' + \
                          'name="versioning" and type="table"'):
            log.warning('EPG database version check failed')
            return 0
        cmd = 'select version from versioning where thing="sql"'
        return self.execute(cmd)[0][0]
