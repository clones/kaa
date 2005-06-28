# -*- coding: iso-8859-1 -*-
# -----------------------------------------------------------------------------
# guide.py - interface to the database
# -----------------------------------------------------------------------------
# $Id$
#
# -----------------------------------------------------------------------------
# kaa-epg - Python EPG module
# Copyright (C) 2002-2005 Dirk Meyer, Rob Shortt, et al.
#
# First Edition: Rob Shortt <rob@tvcentric.com>
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

__all__ = [ 'Guide' ]

# python imports
import time
import logging
from types import *

# kaa.epg imports
from channel import Channel
from program import Program

# get logging object
log = logging.getLogger('epg')

class Guide(object):
    """
    Class for working with the EPG database
    """
    def __init__(self):
        self.selected_index = 0
        self.channel_list = []
        self.channel_dict = {}


    def connect(self, frontent, *args):
        """
        Connect to the database frontent
        """
        exec('from db_%s import Database' % frontent)
        self.db = Database(*args)


    def load(self, tv_channels=[], tv_channels_exclude=[]):
        """
        Load channel listing from the database
        """
        self.exclude_channels = tv_channels_exclude
        # Check TV_CHANNELS and add them to the list
        for c in tv_channels:
            self.add_channel(Channel(c[0], c[1], c[2:], self))

        # Check the db for channels. All channels not in the exclude list
        # will be added if not already in the list
        for c in self.sql_get_channels():
            if c['id'].encode('latin-1', 'ignore') in tv_channels_exclude:
                # Skip channels that we explicitly do not want.
                continue
            if not c['id'] in self.channel_dict.keys():
                self.add_channel(Channel(c['id'], c['display_name'],
                                         c['access_id'], self))


    def close(self):
        """
        Close the database connection.
        """
        self.db.commit()
        self.db.close()


    def __escape_query(self, sql):
        """
        Escape a SQL query in a manner suitable for sqlite
        """
        if not type(sql) in StringTypes:
            return sql
        sql = sql.replace('\'','')
        return sql


    def __escape_value(self, val):
        """
        Escape a SQL value in a manner to be quoted inside a query
        """
        if not type(val) in StringTypes:
            return val
        return val.replace('"', '').replace('\'', '')


    #
    # User Interface
    #
    # Interface functions to get channels / programs
    #

    def update(self, backend, *args, **kwargs):
        """
        Add data with the given backend to the database. The code for the
        real adding is in source_`backend`.py
        """
        exec('import source_%s as backend' % backend)
        backend.update(self, *args, **kwargs)
        self.sql_expire_programs()


    def sort_channels(self):
        """
        Sort the internal channel list (not implemented yet)
        """
        pass


    def add_channel(self, channel):
        """
        Add a channel to the list
        """
        if not self.channel_dict.has_key(channel.id):
            # Add the channel to both the dictionary and the list. This works
            # well in Python since they will both point to the same object!
            self.channel_dict[channel.id] = channel
            self.channel_list.append(channel)


    def __getitem__(self, key):
        """
        Get a channel by position in the list (integer) or by the database
        id (string)
        """
        if isinstance(key, int):
            return self.channel_list[key]
        else:
            return self.channel_dict[key]


    def get_channel(self, start=None, pos=0):
        """
        Get a channel relative to the given channel 'start'. The function
        will start from the beginning of the list if the index is greater
        as the channel list length and wrap to the end if lower zero.
        If start is not given it will return the channel based on the
        selected_index, which is also updated every method call.
        """
        if type(start) in StringTypes:
            start = self.channel_dict.get(start)

        if start:
            cpos = self.channel_list.index(start)
        else:
            cpos = self.selected_index

        self.selected_index = (cpos + pos) % len(self.channel_list)
        return self.channel_list[self.selected_index]


    def get_channel_by_id(self, id):
        """
        Return the channel object based on the given id
        """
        return self.channel_dict[id]


    def search(self, searchstr, by_chan=None, search_title=True,
               search_subtitle=True, search_description=True,
               exact_match=False):
        """
        Return a list of programs with a title similar to the given parameter.
        If by_chan is given, it has to be a valid channel id and only programs
        from this channel will be returned. Result is a list of Programs.
        This function will only return programs with a stop time greater the
        current time.
        """
        if not (search_title or search_subtitle or search_description):
            return []

        now = time.time()
        clause = 'where stop > %d' % now
        if by_chan:
            clause = '%s and channel_id="%s"' % (clause, by_chan)

        clause += ' and ('

        if search_title:
            if exact_match:
                clause = '%s title="%s"' % (clause, searchstr)
            else:
                clause = '%s title like "%%%s%%"' % (clause, searchstr)

        if search_subtitle:
            if search_title: clause += ' or'
            if exact_match:
                clause = '%s subtitle="%s"' % (clause, searchstr)
            else:
                clause = '%s subtitle like "%%%s%%"' % (clause, searchstr)

        if search_description:
            if search_title or search_subtitle: clause += ' or'
            if exact_match:
                clause = '%s description="%s"' % (clause, searchstr)
            else:
                clause = '%s description like "%%%s%%"' % (clause, searchstr)

        clause += ' )'

        query = 'select * from programs %s order by channel_id, start' % clause
        result = []
        for p in self.sql_execute(query):
            if self.channel_dict.has_key(p.channel_id):
                result.append(Program(p.id, p.title, p.start, p.stop,
                                      p.episode, p.subtitle,
                                      description=p['description'],
                                      channel=self.channel_dict[p.channel_id]))
        return result


    def get_program_by_id(self, id):
        """
        Get a program by a database id. Return None if the program is not
        found.
        """
        query = 'select * from programs where id="%s"' % id
        result = self.sql_execute(query)
        if result:
            p = result[0]
            if self.channel_dict.has_key(p.channel_id):
                return Program(p.id, p.title, p.start, p.stop,
                               p.episode, p.subtitle,
                               description=p['description'],
                               channel=self.channel_dict[p.channel_id])
        return None

    #
    # SQL functions
    #
    # This functions will return a sql result and should not by used
    # outside kaa.epg
    #

    def sql_execute(self, query):
        """
        Execute sql query.
        """
        query = self.__escape_query(query)
        try:
            result = self.db.execute(query)
        except TypeError:
            log.exception('execute error')
            return False
        return result


    def sql_commit(self):
        """
        Commit to database.
        """
        self.db.commit()


    def sql_checkTable(self, table=None):
        """
        Check if a table exists.
        """
        if not table:
            return False
        self.db.check_table(table)


    def sql_add_channel(self, id, display_name, access_id):
        """
        Add a channel to the database or replace the information.
        """
        query = 'insert or replace into channels (id, display_name, access_id)\
                 values ("%s", "%s", "%s")' % (id, display_name, access_id)
        self.sql_execute(query)
        self.sql_commit()


    def sql_get_channel(self, id):
        """
        Get a channel.
        """
        query = 'select * from channels where id="%s' % id
        channel = self.sql_execute(query)
        if len(channel):
            return channel[0]


    def sql_get_channels(self):
        """
        Get all channels.
        """
        query = 'select * from channels order by access_id'
        return self.sql_execute(query)


    def sql_remove_channel(self, id):
        """
        Remove a channel from the database.
        """
        query = 'delete from channels where id="%s' % id
        self.sql_execute(query)
        self.sql_commit()


    def sql_get_channel_ids(self):
        """
        Get all channel ids.
        """
        id_list = []
        query = 'select id from channels'
        rows = self.sql_execute(query)
        for row in rows:
            id_list.append(row.id)

        return id_list


    def sql_add_program(self, channel_id, title, start, stop, subtitle='',
                        description='', episode=''):
        """
        Add a program to the database. Make sure that old programs do not
        overlap the new one.
        """
        now = time.time()
        # clean up informations
        title = self.__escape_value(title)
        subtitle = self.__escape_value(subtitle).strip(' \t-_')
        description = self.__escape_value(description).strip(' \t-_')
        episode = self.__escape_value(episode).strip(' \t-_')

        # get possible overlapping programs
        query = 'select * from programs where channel_id="%s" ' % channel_id +\
                'and start>%s and start<%s' % (start, stop)
        rows = self.sql_execute(query)
        if len(rows) and (len(rows) > 1 or rows[0]['start'] != start or \
                          rows[0]['stop'] != stop):
            log.info('changed program time table:')
            # The time table changed. Old programs overlapp new once
            # Better remove everything here
            for row in rows:
                title = row['title'].encode('latin-1', 'replace')
                log.info('delete %s:' % title)
                self.sql_remove_program(row.id)

        # Get program at the given time
        query = 'select * from programs where channel_id="%s" ' % channel_id +\
                'and start=%s' % start
        rows = self.sql_execute(query)
        if len(rows) == 1:
            # An old program is found, check attributes.
            old = rows[0]
            if old['title'] == title:
                # program timeslot is unchanged, see if there's anything
                # that we should update
                if old['subtitle'] != subtitle:
                    query = 'update programs set subtitle="%s" where id=%d'
                    self.sql_execute(query % (subtitle, old.id))
                    self.sql_commit()
                if old['description'] != description:
                    query = 'update programs set description="%s" where id=%d'
                    self.sql_execute(query % (description, old.id))
                    self.sql_commit()
                if old['episode'] != episode:
                    query = 'update programs set episode="%s" where id=%d'
                    self.sql_execute(query % (episode, old.id))
                    self.sql_commit()
                return

            else:
                # old prog and new prog have same times but different title,
                # this is probably a schedule change, remove the old one
                # TODO: check for shifting times and program overlaps
                self.sql_remove_program(old['id'])

        #
        # If we made it here there's no identical program in the table
        # to modify.
        #

        # TODO:
        # Delete any entries of the same program title on the same channel
        # within 10 minues of the start time to somewhat compensate for
        # shifting times.
        # self.sql_execute('delete from programs where channel_id="%s" and \
        #               title="%s" and abs(%s-start)<=600' % \
        #               (channel_id, title, start))

        #
        # If we got this far all we need to do now is insert a new
        # program row.
        #
        if len(title) > 255:
            title = title[:255]

        if len(subtitle) > 255:
            subtitle = subtitle[:255]

        if len(episode) > 255:
            episode = episode[:255]

        if len(description) > 4095:
            episode = episode[:4095]

        query = 'insert into programs (channel_id, title, start, stop, \
                                       subtitle, episode, description) \
                 values ("%s", "%s", %s, %s, "%s", "%s", "%s")' % \
                        (channel_id, title, start, stop,
                         subtitle, episode, description)

        try:
            self.sql_execute(query)
            self.sql_commit()
        except Exception, e:
            log.exception('Unable to add program')


    def sql_get_programs(self, channels, start=0, stop=-1):
        """
        Get a program with start and stop values.

        If channels is given, only get programs from the given channels.

        If start is 0, use current time.

        If stop is 0, only return the programm running at start,
        if stop is -1, return everything from start to the end and
        if stop is something else, return everything between start and stop.
        """
        if not start:
            start = time.time()

        if channels:
            if type(channels) != ListType:
                channels = [ channels, ]
            query = u'select * from programs where'
            for c in channels:
                query = '%s channel_id="%s"' % (query, c)
                if channels.index(c) < len(channels)-1:
                    query = '%s or' % query
            query = u'%s and' % query
        else:
            query = u'SELECT * FROM programs WHERE'

        if stop == 0:
            # only get what's running at time start
            query = u'%s start<=%d and stop>%d' % (query, start, start)
        elif stop == -1:
            # get everything from time start onwards
            query = u'%s ((start<=%d and stop>%d) or start>%d)' % \
                    (query, start, start, start)
        elif stop > 0:
            # get everything from time start to time stop
            query = u'%s start <= %s AND stop >= %s' % \
                    (query, stop, start)
        else:
            return []

        # run the query
        return self.sql_execute('%s order by start' % query)


    def sql_remove_program(self, id):
        """
        Remove a program from the list.
        """
        query = 'delete from programs where id=%d' % id
        self.sql_execute(query)

        query = 'delete from program_category where program_id=%d' % id
        self.sql_execute(query)

        query = 'delete from program_advisory where program_id=%d' % id
        self.sql_execute(query)

        query = 'delete from record_programs where program_id=%d' % id
        self.sql_execute(query)

        query = 'delete from recorded_programs where program_id=%d' % id
        self.sql_execute(query)

        self.sql_commit()


    def sql_expire_programs(self):
        """
        Remove old programs from the database.
        """
        EXPIRE_TIME = time.time() - 12*3600

        query = 'delete from program_category where program_id in \
                 (select id from programs where \
                id not in (select program_id from recorded_programs) \
                and stop<%d)' % EXPIRE_TIME
        rows = self.sql_execute(query)

        query = 'delete from program_advisory where program_id in \
                 (select id from programs where \
                id not in (select program_id from recorded_programs) \
                and stop<%d)' % EXPIRE_TIME
        rows = self.sql_execute(query)

        query = 'delete from programs where \
                 id not in (select program_id from recorded_programs) \
                 and stop<%d' % EXPIRE_TIME
        rows = self.sql_execute(query)

        self.sql_commit()
