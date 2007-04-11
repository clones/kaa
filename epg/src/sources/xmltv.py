# -*- coding: iso-8859-1 -*-
# -----------------------------------------------------------------------------
# source_xmltv.py - XMLTV source for the epg
# -----------------------------------------------------------------------------
# $Id$
# -----------------------------------------------------------------------------
# kaa.epg - EPG Database
# Copyright (C) 2004-2007 Jason Tackaberry, Dirk Meyer, Rob Shortt
#
# First Edition: Jason Tackaberry <tack@sault.org>
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

__all__ = [ 'config', 'update' ]

# python imports
import os
import time
import calendar
import logging

import xml.sax
import xml.sax.saxutils

# kaa imports
from kaa import TEMP
import kaa.notifier

from config_xmltv import config

# get logging object
log = logging.getLogger('xmltv')


class XmltvParser(object):
    """
    Parser class for xmltv files
    """

    mapping = {
            'title':'title',
            'sub-title':'subtitle',
            'episode-num':'episode',
            'category':'genre',
            'desc':'desc',
            'date':'date'
            }

    channels = {}


    def parse(self, filename):
        """
        Create a sax parser and parse the file
        """

        # Create a parser
        parser = xml.sax.make_parser()
        # ignore external dtd file
        parser.setFeature(xml.sax.handler.feature_external_ges, False)

        # create a handler
        dh = xml.sax.ContentHandler()
        dh.startElement = self.startElement
        dh.endElement = self.endElement
        dh.characters = self.characters

        # Tell the parser to use our handler
        parser.setContentHandler(dh)

        self._dict = None
        self._current = None
        self._characters = ''
        # parse the input
        parser.parse('file://' + filename)


    def error(self, exception):
        log.exception(exception)


    def startElement(self, name, attrs):
        """
        startElement function for SAX.

        This will be called whenever we enter an element during parsing.
        Then the attributes will be extracted.
        """
        if name == 'channel':
            # extract attribute "id"
            self._dict = {}
            self._dict['channel_id'] = attrs.get('id', None)
            self._dict['display-name'] = []
        elif name == 'display-name':
            # unfortunately there might be more than one for each channel
            self._dict[name].append(u'')
            self._current = name
        elif name == 'programme':
            self._dict = {}
            # extract "start", "stop" and "id" from attributes
            start = attrs.get('start',None)
            self._dict['start'] = start
            stop = attrs.get('stop',None)
            self._dict['stop'] = stop
            self._dict['channel_id'] = attrs.get('channel',None)
        elif name in self.mapping:
            # translate element name using self.mapping
            name = self.mapping[name]
            # start an empty string for the content of this element
            self._dict[name] = u''
            # and store the name of the current element
            self._current = name


    def characters(self, ch):
        """
        characters function for SAX
        """
        if self._dict is not None and self._current:
            if self._current == 'display-name':
                # there might be more than one display-name
                self._dict['display-name'][-1] +=ch
            else:
                self._dict[self._current] += ch


    def endElement(self, name):
        """
        endElement function for SAX
        """
        if name == 'channel':
            # fill channel info to database
            self.handle_channel(self._dict)
            self._dict = None
        elif name == 'programme':
            # fill programme info to database
            self.handle_programme(self._dict)
            self._dict = None
        # in any case:
        self._current = None


    def timestr2secs_utc(self, timestr):
        """
        Convert a timestring to UTC (=GMT) seconds.

        The format is either one of these two:
        '20020702100000 CDT'
        '200209080000 +0100'
        """
        # This is either something like 'EDT', or '+1'
        try:
            tval, tz = timestr.split()
        except ValueError:
            tval = timestr
            tz   = str(-time.timezone/3600)

        # Is it the '+1' format?
        if tz and tz[0] in ('+', '-'):
            tmTuple = ( int(tval[0:4]), int(tval[4:6]), int(tval[6:8]),
                        int(tval[8:10]), int(tval[10:12]), 0, -1, -1, -1 )
            secs = calendar.timegm( tmTuple )

            adj_neg = int(tz) >= 0
            try:
                min = int(tz[3:5])
            except ValueError:
                # sometimes the mins are missing :-(
                min = 0
            adj_secs = int(tz[1:3])*3600+ min*60

            if adj_neg:
                secs -= adj_secs
            else:
                secs += adj_secs
        else:
            try:
                secs = time.mktime(time.strptime(timestr,'%Y%m%d%H%M%S %Z'))
            except ValueError:
                #try without the timezone
                secs = time.mktime(time.strptime(tval,'%Y%m%d%H%M%S'))
        return float(secs)


    def handle_channel(self, attr):
        """
        put the channel info to the database
        """
        channel = station = name = display = None
        channel_id = attr['channel_id']

        while len(attr['display-name'])>0:
            # This logic expects that the first display-name that appears
            # after an all-numeric and an all-alpha display-name is going
            # to be the descriptive station name.  XXX: check if this holds
            # for all xmltv source.
            content = attr['display-name'].pop(0)
            if not channel and content.isdigit():
                channel = content
            elif not station and content.isalpha():
                station = content
            elif channel and station and not name:
                name = content
            else:
                # something else, just remember it in case we
                # don't have a name later
                display = content

        if not name:
            # set name to something. XXX: this is needed for the german xmltv
            # stuff, maybe others work different. Maybe check the <tv> tag
            # for the used grabber somehow.
            name = display or station


            db_id = self.add_channel(tuner_id=channel,
                                     name=station,
                                     long_name=name)
            self.channels[attr['channel_id']] = [db_id, None]


    def handle_programme(self, attr):
        """
        put the programme info to the database
        """
        # first check the channel_id
        channel_id = attr.pop('channel_id')
        if channel_id not in self.channels:
            log.warning("Program exists for unknown channel '%s'" % channel_id)
            return

        # then there should of course be a title
        title = attr.pop('title')

        # the date element should be a integer
        try:
            date = attr.pop('date')
            fmt = "%Y-%m-%d"
            if len(date) == 4:
                fmt = "%Y"
            attr['date'] = int(time.mktime(time.strptime(date, fmt)))
        except KeyError:
            pass

        # then the start time
        start = self.timestr2secs_utc(attr.pop('start'))

        # stop time is more complicated, as it is not always given
        db_id, last_prog = self.channels[channel_id]
        if last_prog:
            # There is a previous program for this channel with no stop time,
            # so set last program stop time to this program start time.
            # XXX This only works in sorted files. I guess it is ok to force the
            # user to run tv_sort to fix this. And IIRC tv_sort also takes care of
            # this problem.
            last_start, last_title, last_attr = last_prog
            self.add_program(db_id, last_start, start, last_title, **last_attr)
            self.channels[channel_id][1] = None
        try:
            stop = self.timestr2secs_utc(attr.pop('stop'))
            # we have all info, let's fill it to the database
            self.add_program(db_id, start, stop, title, **attr)
        except:
            # there is not stop time for this
            self.channels[channel_id][1] = (start, title, attr)


@kaa.notifier.execute_in_thread('epg')
def update(epg):
    """
    Interface to source_xmltv.
    """
    if config.grabber:
        log.info('grabbing listings using %s', config.grabber)
        xmltv_file = os.path.join(TEMP, 'TV.xml')
        if config.data_file:
            xmltv_file = config.data_file
        log_file = os.path.join(TEMP, 'TV.xml.log')
        # TODO: using os.system is ugly because it blocks ... but we can make this
        # nicer using kaa.notifier.Process later. We are inside a thread so it
        # seems to be ok.
        ec = os.system('%s --output %s --days %s >%s 2>%s' % \
                       (config.grabber, xmltv_file, config.days, log_file, log_file))
        if not os.path.exists(xmltv_file) or ec:
            log.error('grabber failed, see %s', log_file)
            return

        if config.sort:
            log.info('sorting listings')
            shutil.move(xmltv_file, xmltv_file + '.tmp')
            os.system('%s --output %s %s.tmp >>%s 2>>%s' % \
                      (config.sort, xmltv_file, xmltv_file, log_file, log_file))
            os.unlink(xmltv_file + '.tmp')
            if not os.path.exists(xmltv_file):
                log.error('sorting failed, see %s', log_file)
                return
        else:
            log.info('not configured to use tv_sort, skipping')
    else:
        xmltv_file = config.data_file

    # Now we have a xmltv file and need to parse it
    log.info('parse xmltv file %s' % xmltv_file)
    parser = XmltvParser()
    parser.add_channel = epg.add_channel
    parser.add_program = epg.add_program
    parser.parse(xmltv_file)

    epg.add_program_wait()
    return True
