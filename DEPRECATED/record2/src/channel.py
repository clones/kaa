# -*- coding: iso-8859-1 -*-
# -----------------------------------------------------------------------------
# channels.py - Read channels.conf to Channel objects
# -----------------------------------------------------------------------------
# $Id$
#
# -----------------------------------------------------------------------------
# kaa-record - A recording module
# Copyright (C) 2007 Sönke Schwardt, Dirk Meyer
#
# First Edition: Sönke Schwardt <bulk@schwardtnet.de>
# Maintainer:    Sönke Schwardt <bulk@schwardtnet.de>
#
# Please see the file AUTHOR for a complete list of authors.
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
import re
import sys
import types
import logging

# get logging object
log = logging.getLogger('record.channel')

class Channel(object):
    # TODO / FIXME add missing compare function
    map_hierarchy = { 'default': 'AUTO',
                      '999': 'AUTO',
                      '0': 'NONE',
                      '1': '1',
                      '2': '2',
                      '4': '4' }

    map_bandwidth = { 'default': 'AUTO',
                      '999': 'AUTO',
                      '6': '6_MHZ',
                      '7': '7_MHZ',
                      '8': '8_MHZ' }

    map_transmissionmode = { 'default': 'AUTO',
                             '999': 'AUTO',
                             '2': '2K',
                             '8': '8K' }

    map_guardinterval = { 'default': 'AUTO',
                          '999': 'AUTO',
                          '4':  '1/4',
                          '8':  '1/8',
                          '16': '1/16',
                          '32': '1/32' }

    map_modulation = { 'default': 'AUTO',
                       '999': 'AUTO',
                       '16': 'QAM_16',
                       '32': 'QAM_32',
                       '64': 'QAM_64',
                       '128': 'QAM_128',
                       '256': 'QAM_256' }

    map_fec = { 'default': 'AUTO',
                '999': 'AUTO',
                '0': 'NONE',
                '12': '1/2',
                '23': '2/3',
                '34': '3/4',
                '45': '4/5',
                '56': '5/6',
                '67': '6/7',
                '78': '7/8',
                '89': '8/9' }

    map_inversion = { 'default': 'AUTO',
                      '999': 'AUTO',
                      '0': 'OFF',
                      '1': 'ON' }



    def __init__(self, line):
        self.re_dvbt = re.compile('^.*?:\d+:([ICDMBTGY]\d+)+:T:\d+:\d+:\d+(=\w+)?(,\d+(=\w+)?)?(;\d+(=\w+)?(,\d+(=\w+)?)?)*:\d+:\d+:\d+:\d+:\d+:\d+')
        self.re_dvbc = re.compile('^.*?:\d+:([ICDMBTGY]\d+)+:C:\d+:\d+:\d+(=\w+)?(,\d+(=\w+)?)?(;\d+(=\w+)?(,\d+(=\w+)?)?)*:\d+:\d+:\d+:\d+:\d+:\d+')
        self.re_dvbs = re.compile('^.*?:\d+:[HV]([ICDMBTGY]\d+)*:S\d+(\.\d+)?[EeWw]:\d+:\d+:\d+(=\w+)?(,\d+(=\w+)?)?(;\d+(=\w+)?(,\d+(=\w+)?)?)*:\d+:\d+:\d+:\d+:\d+:\d+', re.IGNORECASE)


        self.config = { }
        self.line = line.strip('\n')
        self.cfgtype = None

        if len(self.line) == 0 or self.line[0] == '#':
            self.cfgtype = 'COMMENT'
            return
        if self.re_dvbt.match(line):
            self.cfgtype = 'DVB-T'
            return self.parse_vdr_style(line)
        if self.re_dvbc.match(line):
            self.cfgtype = 'DVB-C'
            return self.parse_vdr_style(line)
        if self.re_dvbs.match(line):
            self.cfgtype = 'DVB-S'
            return self.parse_vdr_style(line)

        cells = line.split(':')
        if len(cells) == 13 and cells[2].startswith('INVERSION_'):
            self.cfgtype = 'DVB-T'
            return self.parse_dvbt(cells)

        log.error('failed to parse config line:\n%s' % self.line)
        return None


    def parse_vdr_style(self, line):

        cells = self.line.split(':')

        if ';' in cells[0]:
            self.config['name'] = cells[0].split(';')[0]
            self.config['bouquet'] = cells[0].split(';')[1]
        else:
            self.config['name'] = cells[0]
            self.config['bouquet'] = ''

        self.config['name'] = self.config['name'].replace('|', ':')
        self.config['bouquet'] = self.config['bouquet'].replace('|', ':')
        self.config['frequency'] = int(cells[1])

        # get params
        re_params = re.compile('([ICDMBTGYHV]\d*)',re.IGNORECASE)
        for param in re_params.findall(cells[2].upper()):
            if param[0]=='I':
                self.config['inversion'] = param[1:]
            if param[0]=='C':
                self.config['code-rate-high-prio'] = param[1:]
            if param[0]=='D':
                self.config['code-rate-low-prio'] = param[1:]
            if param[0]=='M':
                self.config['modulation'] = param[1:]
            if param[0]=='B':
                self.config['bandwidth'] = param[1:]
            if param[0]=='T':
                self.config['transmission-mode'] = param[1:]
            if param[0]=='G':
                self.config['guard-interval'] = param[1:]
            if param[0]=='Y':
                self.config['hierarchy'] = param[1:]
            if param[0]=='H':
                self.config['horizontal_polarization'] = True
            if param[0]=='V':
                self.config['horizontal_polarization'] = False
            if param[0]=='R':
                self.config['circular_polarization_right'] = param[1:]
            if param[0]=='L':
                self.config['circular_polarization_left'] = param[1:]

        self.config['type'] = cells[3][0]
        if len(cells[3]) > 1:
            self.config['source'] = cells[3][1:]

        self.config['symbol-rate'] = int(cells[4])
        self.config['vpid'] = cells[5]

        self.config['apids'] = []
        for i in cells[6].split(';'):
            lst = []
            for t in i.split(','):
                if '=' in t:
                    lst.append( tuple(t.split('=')) )
                else:
                    lst.append( ( t, '' ) )
            self.config['apids'].extend(lst)

        self.config['tpid'] = cells[7]
        self.config['caid'] = cells[8]
        self.config['sid'] = cells[9]
        self.config['nid'] = cells[10]
        self.config['tid'] = cells[11]
        self.config['rid'] = cells[12]

        if self.config['frequency'] > 0:
            while self.config['frequency'] < 1000000:
                self.config['frequency'] *= 1000

        self.map_config( 'hierarchy', self.map_hierarchy )
        self.map_config( 'bandwidth', self.map_bandwidth )
        self.map_config( 'transmission-mode', self.map_transmissionmode )
        self.map_config( 'guard-interval', self.map_guardinterval )
        self.map_config( 'modulation', self.map_modulation )
        self.map_config( 'code-rate-low-prio', self.map_fec )
        self.map_config( 'code-rate-high-prio', self.map_fec )
        self.map_config( 'inversion', self.map_inversion )


    def parse_dvbt(self, cells):
        if ';' in cells[0]:
            self.config['name'] = cells[0].split(';')[0]
            self.config['bouquet'] = cells[0].split(';')[1]
        else:
            self.config['name'] = cells[0]
            self.config['bouquet'] = ''

        self.config['name'] = self.config['name'].replace('|', ':')
        self.config['bouquet'] = self.config['bouquet'].replace('|', ':')
        self.config['frequency'] = int(cells[1])

        self.config['inversion'] = cells[2][10:]
        self.config['bandwidth'] = cells[3][10:]
        self.config['code-rate-low-prio'] = cells[4][4:]
        self.config['code-rate-high-prio'] = cells[5][4:]
        self.config['modulation'] = cells[6]
        self.config['transmission-mode'] = cells[7][18:]
        self.config['guard-interval'] = cells[8][15:]
        self.config['hierarchy'] = cells[9][10:]
        self.config['vpid'] = cells[10]
        self.config['apids'] = [ cells[11] ]
        self.config['tpid'] = cells[12]


    def map_config(self, key, keydict):
        if not self.config.has_key( key ):
            return
        if self.config[ key ] in keydict.keys():
            self.config[ key ] = keydict[ self.config[ key ] ]
        else:
            log.warn('failed to parse %s (%s) - using default %s',
                     key, self.config[key], keydict['default'])
            self.config[key] = keydict[ 'default' ]


    def __repr__(self):
        return '<kaa.record.Channel %s>' % self.config['name']


    def __str__(self):
        return '%s channel: %-25s [%-25s] (vpid=%s  apids=%s)' \
               % (self.cfgtype, self.config['name'], self.config['bouquet'],
                  self.config['vpid'], self.config['apids'])



class Multiplex(object):
    def __init__(self, name, frequency):
        self.name = name
        self.frequency = frequency
        self.chanlist = []


    # TODO FIXME add missing compare functions
    # TODO FIXME add __contains__, __getitem__, __setitem__

    def add(self, chan):
        if (chan.config['frequency'] != self.frequency):
            return False
        # TODO / FIXME check if channel is already present in multiplex
        self.chanlist.append(chan)
        return True


    def remove(self, channame):
        # TODO FIXME return value returns True if channel with channame
        # was found and deleted otherwise False
        self.chanlist = filter(lambda chan: chan.config['name'] == channame,
                               self.chanlist)
        return True


    def keys(self):
        """ return names of known channels within this multiplex """
        result = []
        for chan in self.chanlist:
            result.append(chan.config['name'])
        return result


    def __getitem__(self, key):
        """
        returns channel specified by integer (position) or by name.
        if specified by name the first matching one is chosen.
        """
        if type(key) is types.IntType:
            return self.chanlist[key]

        if type(key) is types.StringType:
            for chan in self.chanlist:
                if chan.config['name'] == key:
                    return chan
            raise KeyError()
        raise TypeError()


    def __repr__(self):
        return '<kaa.record.Multiplex: %s' % self.name


    def __str__(self):
        s = 'Multiplex: %-25s (f=%s)\n' % (self.name, self.frequency)
        for chan in self.chanlist:
            s += str(chan) + '\n'
        return s + '\n'



class ConfigFile(object):
    def __init__(self, cfgname):
        self.cfgtype = None
        self.multiplexlist = [ ]

        # read config
        self.f = open(cfgname)
        for line in self.f:
            channel = Channel(line)

            if channel.cfgtype == None:
                # ignore bad line
                continue

            if self.cfgtype == None:
                self.cfgtype = channel.cfgtype
            elif self.cfgtype is not channel.cfgtype:
                if channel.cfgtype != 'COMMENT':
                    log.warn('Oops: mixed mode config file!')
                    log.warn('Drop: %s' % line.strip())
                continue

            for mplex in self.multiplexlist:
                added = mplex.add( channel )
                if added:
                    log.info('added channel %s to mplex %s',
                             channel.config['name'], mplex.name)
                    break
            else:
                mplex = Multiplex( channel.config['frequency'],
                                   channel.config['frequency'], )
                mplex.add( channel )
                self.multiplexlist.append(mplex)
                log.info('added channel %s to new mplex %s',
                         channel.config['name'], mplex.name)


    # TODO FIXME add missing __getitem__, __contains__
    # get channel config by
    # channelconfreader[MULTIPLEXNAME][CHANNELNAME] or
    # channelconfreader[MULTIPLEXINDEX][CHANNELINDEX]

    def keys(self):
        """ return names of known multiplexes """
        result = []
        for mplex in self.multiplexlist:
            result.append(mplex.name)
        return result


    def __getitem__(self, key):
        """
        returns multiplex specified by integer (position) or by name.
        if specified by name the first matching one is chosen.
        """
        if type(key) is types.IntType:
            return self.multiplexlist[key]

        if type(key) is types.StringType:
            for mplex in self.multiplexlist:
                if mplex.name == key:
                    return mplex
            raise KeyError()
        raise TypeError()


    def get_channel(self, key):
        for mplex in self.multiplexlist:
            if key in mplex.keys():
                return mplex[key]
        return None

    def __str__(self):
        s = 'MULTIPLEX LIST:\n'
        s += '===============\n'
        for mplex in self.multiplexlist:
            s += str(mplex)
        return s


if __name__ == '__main__':
    log = logging.getLogger()
    for l in log.handlers:
        log.removeHandler(l)
    formatter = logging.Formatter('%(levelname)s %(module)s'+ \
                                  '(%(lineno)s): %(message)s')
    handler = logging.StreamHandler()
    handler.setFormatter(formatter)
    log.addHandler(handler)

    logging.getLogger().setLevel(logging.DEBUG)
    ccr = ConfigFile(sys.argv[1])
    print ccr
    print '---------------'
    print 'find channel "n-tv":'
    print ccr.get_channel('n-tv')
    print '---------------'
    print 'find channel "n-tv":'
    print ccr.get_channel('n-tv').config

