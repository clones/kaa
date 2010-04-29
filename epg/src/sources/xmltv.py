# -*- coding: iso-8859-1 -*-
# -----------------------------------------------------------------------------
# source_xmltv.py - XMLTV source for the epg
# -----------------------------------------------------------------------------
# $Id$
# -----------------------------------------------------------------------------
# kaa.epg - EPG Database
# Copyright (C) 2004-2008 Jason Tackaberry, Dirk Meyer, Rob Shortt
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
import kaa

# config file
from config_xmltv import config as sourcecfg
from config import config

# get logging object
log = logging.getLogger('epg.xmltv')

def timestr2secs_utc(timestr):
    """
    Convert a timestring to UTC (=GMT) seconds.

    The format is either one of these two:
    '20020702100000 CDT'
    '200209080000 +0100'
    """
    # This is either something like 'EDT', or '+1'
    try:
        tval, tz = timestr.split()
    except ValueError, e:
        tval = timestr
        # ugly, but assume current timezone
        tz   = time.tzname[time.daylight]
    # now we convert the timestring using the current timezone
    secs = int(time.mktime(time.strptime(tval,'%Y%m%d%H%M%S')))
    # The timezone is still missing. The %Z handling of Python
    # seems to be broken, at least for me CEST and UTC return the
    # same value with time.strptime. This means we handle it now
    # ourself.
    if tz in time.tzname:
        # the timezone is something we know
        if list(time.tzname).index(tz):
            # summer time
            return secs + time.altzone
        # winter (normal) time
        return secs + time.timezone
    if tz in ('UTC', 'GMT'):
        # already UTC
        return secs
    # timeval [+-][hh]00
    # FIXME: my xmltv file uses +0000 so I can not test here.
    # It should be secs - tz and maybe it is +
    return secs - int(tz) * 36

class XmltvParser(object):
    """
    Parser class for xmltv files
    """
    mapping = {
            'title':'title',
            'sub-title':'subtitle',
            'episode-num':'episode',
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
        if filename.startswith('<?xml'):
            log.info('parse provided xmltv string')
            parser.feed(filename)
        else:
            log.info('parse xmltv file %s' % filename)
            parser.parse('file://' + os.path.abspath(filename))

    def error(self, exception):
        """
        Parse error callback
        """
        log.exception(exception)

    def startElement(self, name, attrs):
        """
        startElement function for SAX.

        This will be called whenever we enter an element during parsing.
        Then the attributes will be extracted.
        """
        if kaa.main.is_stopped():
            raise SystemExit
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
        elif name == 'category':
            self._dict.setdefault('genres', []).append(u'')
            self._current = name
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
                self._dict['display-name'][-1] += ch
            elif self._current == 'category':
                self._dict['genres'][-1] += ch
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
        if not channel:
            channel = channel_id
            
        db_id = self.add_channel(tuner_id=channel, name=station, long_name=name)
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
        # determine format of date element
        try:
            date = attr.pop('date')
            if len(date) == 4 and date.isdigit():
                attr['year'] = int(date)
                del attr['date']
            else:
                attr['date'] = int(time.mktime(time.strptime(date, '%Y-%m-%d')))
        except KeyError:
            pass
        # then the start time
        start = timestr2secs_utc(attr.pop('start'))
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
            stop = timestr2secs_utc(attr.pop('stop'))
            # we have all info, let's fill it to the database
            self.add_program(db_id, start, stop, title, **attr)
        except:
            # there is not stop time for this
            self.channels[channel_id][1] = (start, title, attr)


@kaa.threaded('kaa.epg::update')
def update(epg, xmltv_file=None):
    """
    Interface to source_xmltv.
    """
    if not xmltv_file and config.xmltv.grabber:
        log.info('grabbing listings using %s', config.xmltv.grabber)
        xmltv_file = kaa.tempfile('TV.xml')
        if config.xmltv.data_file:
            xmltv_file = config.xmltv.data_file
        log_file = kaa.tempfile('TV.xml.log')
        # using os.system is ugly because it blocks ... but we are inside a thread so it
        # seems to be ok.
        ec = os.system('%s --output %s --days %s >%s 2>%s' % \
                       (config.xmltv.grabber, xmltv_file, config.days, log_file, log_file))
        if not os.path.exists(xmltv_file) or ec:
            log.error('grabber failed, see %s', log_file)
            return
        if config.xmltv.sort:
            log.info('sorting listings')
            shutil.move(xmltv_file, xmltv_file + '.tmp')
            os.system('%s --output %s %s.tmp >>%s 2>>%s' % \
                      (config.xmltv.sort, xmltv_file, xmltv_file, log_file, log_file))
            os.unlink(xmltv_file + '.tmp')
            if not os.path.exists(xmltv_file):
                log.error('sorting failed, see %s', log_file)
                return
        else:
            log.info('not configured to use tv_sort, skipping')
    elif not xmltv_file:
        xmltv_file = config.xmltv.data_file
    # Now we have a xmltv file and need to parse it
    parser = XmltvParser()
    parser.add_channel = epg.add_channel
    parser.add_program = epg.add_program
    parser.parse(xmltv_file)
    return True
