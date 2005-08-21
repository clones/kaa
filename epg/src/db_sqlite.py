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

# kaa imports
import kaa.notifier

# sqlite
import sqlite

# epg imports
import schema
import db_base


class Database(db_base.Database):
    """
    Database class for sqlite usage
    """
    OperationalError = sqlite.OperationalError

    def create(self):
        """
        Craete the db.
        """
        self.cursor.execute(schema.schema)
        self.db.commit()


    def open(self, dbpath):
        """
        Open the db.
        """
        while 1:
            # connect to the database
            try:
                self.db = sqlite.connect(dbpath, client_encoding='utf-8',
                                         timeout=10)
                break
            except sqlite.OperationalError, e:
                # keep main loop alive
                kaa.notifier.step(False, False)
        self.cursor = sqlite.Cursor(self.db, rowclass=tuple)
