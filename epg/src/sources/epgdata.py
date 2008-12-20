# -*- coding: iso-8859-1 -*-
# -----------------------------------------------------------------------------
# source_epgdata.py -  get epg data from www.epgdata.com
# -----------------------------------------------------------------------------
# $Id:
# -----------------------------------------------------------------------------
# kaa.epg - EPG Database
# Copyright (C) 2007 Jason Tackaberry, Dirk Meyer, Rob Shortt
#
# First Edition: Tanja Kotthaus <owigera@web.de>
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
import glob
import logging

import xml.sax
import xml.sax.saxutils

# kaa imports
import kaa

# config file
from config import config

# get logging object
log = logging.getLogger('epg.epgdata')


class BaseParser(object):

    def parse(self, filename):

        # Create a parser
        parser = xml.sax.make_parser()

        # create a handler
        dh = xml.sax.ContentHandler()
        dh.startElement = self.startElement
        dh.endElement = self.endElement
        dh.characters = self.characters

        # Tell the parser to use our handler
        parser.setContentHandler(dh)

        self._dict = None
        self._characters = ''
        # parse the input, add file:// so the parser will find
        # the dtd for program files.
        parser.parse('file://' + filename)


    def error(self, exception):
        log.exception(exception)


    def startElement(self, name, attrs):
        """
        startElement function for SAX.

        This will be called whenever we enter a <ch> element during parsing.
        Then the attributes will be extracted.
        """
        if name == 'data':
            self._dict = {}
            self._current = None
        elif self._dict is not None and name in self.mapping:
            name = self.mapping[name]
            self._dict[name] = u''
            self._current = name


    def characters(self, ch):
        """
        characters function for SAX
        """
        if self._dict is not None and self._current:
            self._dict[self._current] += ch


    def endElement(self, name):
        """
        endElement function for SAX
        """
        if name == 'data':
            self.handle(self._dict)
            self._dict = None
        else:
            self._current = None


class ChannelParser(BaseParser, dict):
    # the meaning of the tags that are used in the channel*.xml files can
    # be found in the header of each channel*.xml file.
    mapping = {
        'ch0':'tvchannel_name',
        'ch1':'tvchannel_short',
        'ch4':'tvchannel_id',
        'ch11':'tvchannel_dvb'
    }

    def handle(self, attr):
        if attr['tvchannel_id'] in self:
            # we had this already
            return
        db_id = self.add_channel(
            tuner_id=attr['tvchannel_dvb'],
            name=attr['tvchannel_short'],
            long_name=attr['tvchannel_name'])
        self[attr['tvchannel_id']] = db_id


class MetaParser(BaseParser, dict):
    mapping = {
        'g0':'id',    # genre_id
        'g1':'name',  # genre
        'ca0':'id',   # category_id
        'ca2':'name'  # category
    }

    def handle(self, data):
        self[data['id']] = data['name']


class ProgramParser(BaseParser):
    # the meaning of the tags that epgdata.com uses can be found in the qe.dtd file
    # which is included in the zip archive that contains also the epg data.
    mapping = {
        'd2':'channel_id',
        'd4':'start',
        'd5':'stop',
        'd10':'category',
        'd25':'genres',
        'd19':'title',
        'd20':'subtitle',
        'd21':'desc',
        'd32':'coutry',
        'd33':'date',
        'd34':'presenter',
        'd36':'director',
        'd37':'actor',
        'd40':'icon'
    }

    def timestr2secs_utc(self, timestr):
        """
        Convert the timestring to UTC (=GMT) seconds.

        The time format in the epddata is:
        '2002-09-08 00:00:00'
        The timezone is german localtime, which is CET or CEST.
        """
        secs = time.mktime(time.strptime(timestr, '%Y-%m-%d %H:%M:%S'))
        return secs


    def handle(self, attr):
        if 'date' in attr:
            date = attr['date']
            # try to guess the format of the date
            if len(date.split('/'))==2:
                # if it is '1995/96', take the first year
                date = date.split('/')[0]
            elif len(date.split('-'))==2:
                # if it is '1999-2004', take the first year
                date = date.split('-')[0]
            del attr['date']
            if len(date) == 4:
                attr['year'] = int(date)

        for metadata in ('category', 'genres'):
            # FIXME: genres should be a list
            if metadata in attr:
                if attr[metadata] in self.metadata:
                    attr[metadata] = self.metadata[attr[metadata]]
                else:
                    attr[metadata] = u''
        # start and stop time must be converted according to our standards
        start = self.timestr2secs_utc(attr.pop('start'))
        stop = self.timestr2secs_utc(attr.pop('stop'))
        # there of course must be a title
        title = attr.pop('title')
        # translate channel_id to db_id
        db_id = self.channels[attr.pop('channel_id')]
        # fill this program to the database
        self.add_program(db_id, start, stop, title, **attr)


@kaa.threaded('epg')
def update(epg):
    """
    Interface to source_epgdata.
    """
    if not config.epgdata.pin:
        log.error('PIN for epgdata.com is missing in tvserver.conf')
        return False

    # create a tempdir as working area
    tempdir = kaa.tempfile('epgdata')
    if not os.path.isdir(tempdir):
        os.mkdir(tempdir)
    # and clear it if needed
    for i in glob.glob(os.path.join(tempdir,'*')):
       os.remove(i)

    # temp file
    tmpfile = os.path.join(tempdir,'temp.zip')
    # logfile
    logfile = kaa.tempfile('epgdata.log')

    # empty list for the xml docs
    docs = []
    # count of the nodes that have to be parsed
    nodes = 0


    # create download adresse for meta data
    address = 'http://www.epgdata.com/index.php'
    address+= '?action=sendInclude&iLang=de&iOEM=xml&iCountry=de'
    address+= '&pin=%s' % config.epgdata.pin
    address+= '&dataType=xml'

    # remove old file if needed
    try:
        os.remove(tmpfile)
    except OSError:
         pass
    # download the meta data file
    log.info ('Downloading meta data')
    # FIXME: don't rely on wget
    exit = os.system('wget -N -O %s "%s" >>%s 2>>%s'
                    %(tmpfile, address, logfile, logfile))
    if not os.path.exists(tmpfile) or exit:
        log.error('Cannot get file from epgdata.com, see %s' %logfile)
        return False
    # and unzip the zip file
    log.info('Unzipping data for meta data')
    # FIXME: don't rely on unzip (can probably use zipfile module)
    exit = os.system('unzip -uo -d %s %s >>%s 2>>%s'
                    %(tempdir, tmpfile, logfile, logfile))
    if exit:
        log.error('Cannot unzip the downloaded file, see %s' %logfile)
        return False

    # list of channel info xml files
    chfiles = glob.glob(os.path.join(tempdir,'channel*.xml'))
    if len(chfiles)==0:
        log.error('no channel xml files for parsing')
        return False

    # parse this files
    channels = ChannelParser()
    channels.add_channel = epg.add_channel
    for xmlfile in chfiles:
        # return the list of channels from the config file
        channels.parse(xmlfile)

    metadata = MetaParser()
    metadata.parse(os.path.join(tempdir, 'genre.xml'))
    metadata.parse(os.path.join(tempdir, 'category.xml'))

    # create download adresse for programm files
    address = 'http://www.epgdata.com/index.php'
    address+= '?action=sendPackage&iLang=de&iOEM=xml&iCountry=de'
    address+= '&pin=%s' % config.epgdata.pin
    address+= '&dayOffset=%s&dataType=xml'

    # get the file for each day
    for i in range(0, int(config.days)):
            # remove old file if needed
            try:
                os.remove(tmpfile)
            except OSError:
                pass
            # download the zip file
            log.info('Getting data for day %s' %(i+1))
            exit = os.system('wget -N -O %s "%s" >>%s 2>>%s'
                            %(tmpfile, address %i, logfile, logfile))
            if not os.path.exists(tmpfile) or exit:
                log.error('Cannot get file from epgdata.com, see %s' %logfile)
                return False
            # and unzip the zip file
            log.info('Unzipping data for day %s' %(i+1))
            exit = os.system('unzip -uo -d %s %s >>%s 2>>%s'
                            %(tempdir, tmpfile, logfile, logfile))
            if exit:
                log.error('Cannot unzip the downloaded file, see %s' %logfile)
                return False

    # list of program xml files that must be parsed
    progfiles = glob.glob(os.path.join(tempdir,'*de_q[a-z].xml'))
    if len(progfiles)==0:
        log.warning('no progam xml files for parsing')

    # parse the progam xml files
    prgparser = ProgramParser()
    prgparser.channels = channels
    prgparser.metadata = metadata
    prgparser.add_program = epg.add_program
    log.info('found %s files' % len(progfiles))
    for xmlfile in progfiles:
        log.info('process %s' % xmlfile)
        prgparser.parse(xmlfile)
    return True
