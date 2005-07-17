# -*- coding: iso-8859-1 -*-
# -----------------------------------------------------------------------------
# db_sqlite.py - interface to sqlite
# -----------------------------------------------------------------------------
# $Id$
#
# -----------------------------------------------------------------------------
# kaa-epg - Python EPG module
# Copyright (C) 2002-2005 Dirk Meyer, Rob Shortt, et al.
#
# First Edition: Dirk Meyer <dmeyer@tzi.de>
# Maintainer:    Dirk Meyer <dmeyer@tzi.de>
#                Rob Shortt <rob@tvcentric.com>
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

# sqlite
import sqlite

# epg imports
import schema

# get logging object
log = logging.getLogger('epg')

latest_version = "0.1.1"

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

        while 1:
            # connect to the database
            try:
                self.db = sqlite.connect(dbpath, client_encoding='utf-8',
                                         timeout=10)
                break
            except sqlite.OperationalError, e:
                # keep main loop alive
                kaa.notifier.step(False, False)

        self.cursor = self.db.cursor()
        if not dbmissing:
            try:
                ver = self.get_version()
                log.debug('EPG database version %s' % ver)
                if ver != latest_version:
                    warning = 'EPG database out of date, latest version is %s'
                    log.warning(warning % latest_version)
                    if ver == "0.0.0" and latest_version == "0.1.1":
                        for cmd in schema.update['0.1.1']:
                            self.execute(cmd, True)
                        self.commit()
            except AttributeError:
                log.warning('Invalid database, creating a new one')
                dbmissing = True
                os.unlink(dbpath)

        if dbmissing:
            self.execute(schema.schema, True)
            self.commit()


    def commit(self):
        """
        Commit changes to database.
        """
        self.db.commit()


    def close(self):
        """
        Close database connection.
        """
        self.db.close()


    def execute(self, query, as_list):
        """
        Execute a query. The parameter as_list has no effect on this backend.
        """
        while 1:
            try:
                self.cursor.execute(query)
                return self.cursor.fetchall()
            except sqlite.OperationalError, e:
                # keep main loop alive
                kaa.notifier.step(False, False)


    def get_version(self):
        """
        Get database version information.
        """
        if self.check_table('versioning'):
            cmd = 'select version from versioning where thing="sql"'
            return self.execute(cmd, True)[0][0]
        else:
            log.warning('EPG database version check failed')
            raise AttributeError('Broken DB')


    def check_table(self, table=None):
        """
        Check if a table exists.
        """
        if not table:
            return False
        # verify the table exists
        if not self.execute('select name from sqlite_master where ' + \
                            'name="%s" and type="table"' % table, True):
            return None
        return table
