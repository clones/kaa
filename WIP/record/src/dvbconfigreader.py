#!/usr/bin/python
# -*- coding: iso-8859-1 -*-
# -----------------------------------------------------------------------------
# device.py - Devices for recordings
# -----------------------------------------------------------------------------
# $Id$
#
# This file defines the possible devices for recording.
#
# -----------------------------------------------------------------------------
# kaa-record - A recording module
# Copyright (C) 2007 Sönke Schwardt, Dirk Meyer
#
# First Edition: Sönke Schwardt <bulk@schwardtnet.de>
# Maintainer:    Sönke Schwardt <bulk@schwardtnet.de>
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

# python imports
import re
import sys
import types
import logging
import traceback

# get logging object
log = logging.getLogger('record')

# TODO FIXME add more debug output to logger

#
# DVB-S
#ARD - Das Erste:11836:h:S19.2E:27500:101:102:104:0:28106:0:0:0
#ARD - Bayerisches FS:11836:h:S19.2E:27500:201:202:204:0:28107:0:0:0
#
# DVB-T
#Das Erste:706000:I999C23D23M16B8T8G4Y0:T:27500:257:258:260:0:224:0:0:0
#ZDF:522000:I999C23D12M16B8T8G4Y0:T:27500:545:546,547;559:551:0:514:0:0:0
#
# DVB-C
#PREMIERE SERIE:346000:M64:C:6900:2559:2560;2563:32:1:16:133:2:0
#PREMIERE KRIMI:346000:M64:C:6900:2815:2816:32:1:23:133:2:0
#

class DVBChannel:
    # TODO / FIXME add missing compare function
    map_hierarchy = { 'default': 'AUTO',
                      '999': 'AUTO',
                      '0': '0',
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
        self.re_dvbt = re.compile('^.*?:\d+:([ICDMBTGY]\d+)+:T:\d+:\d+:\d+(,\d+)?(;\d+(,\d+)?)*:\d+:\d+:\d+:\d+:\d+:\d+')
        self.re_dvbc = re.compile('^.*?:\d+:([ICDMBTGY]\d+)+:C:\d+:\d+:\d+(,\d+)?(;\d+(,\d+)?)*:\d+:\d+:\d+:\d+:\d+:\d+')
        self.re_dvbs = re.compile('^.*?:\d+:[HV]([ICDMBTGY]\d+)*:S\d+(\.\d+)?[EeWw]:\d+:\d+:\d+(,\d+)?(;\d+(,\d+)?)*:\d+:\d+:\d+:\d+:\d+:\d+', re.IGNORECASE)


        self.config = { }
        self.line = line.strip('\n')
        self.cfgtype = None

        if self.line[0] == '#':
            self.cfgtype = 'COMMENT'
        if self.re_dvbt.match(line):
            self.cfgtype = 'DVB-T'
        if self.re_dvbc.match(line):
            self.cfgtype = 'DVB-C'
        if self.re_dvbs.match(line):
            self.cfgtype = 'DVB-S'

        if self.cfgtype == None:
            log.error('failed to parse config line:\n%s' % self.line)
            return None

        cells = self.line.split(':')
        
        self.config['name'] = cells[0]
        self.config['frequency'] = cells[1]
        
        # get params
        re_params = re.compile('([ICDMBTGYHV]\d*)',re.IGNORECASE)
        for param in re_params.findall(cells[2].upper()):
            if param[0]=='I':
                self.config['inversion'] = param[1:]
            if param[0]=='C':
                self.config['dataratehigh'] = param[1:]
            if param[0]=='D':
                self.config['dataratelow'] = param[1:]
            if param[0]=='M':
                self.config['modulation'] = param[1:]
            if param[0]=='B':
                self.config['bandwidth'] = param[1:]
            if param[0]=='T':
                self.config['transmissionmode'] = param[1:]
            if param[0]=='G':
                self.config['guardinterval'] = param[1:]
            if param[0]=='Y':
                self.config['hierarchie'] = param[1:]
            if param[0]=='H':
                self.config['horizontal_polarization'] = param[1:]
            if param[0]=='V':
                self.config['vertical_polarization'] = param[1:]
            if param[0]=='R':
                self.config['circular_polarization_right'] = param[1:]
            if param[0]=='L':
                self.config['circular_polarization_left'] = param[1:]

        self.config['type'] = cells[3][0]
        if len(cells[3]) > 1:
            self.config['source'] = cells[3][1:]

        self.config['symbolrate'] = cells[4]
        self.config['vpid'] = cells[5]

        self.config['apids'] = []
        for i in cells[6].split(';'):
            lst = []
            for t in i.split(','):
                lst.append(t)
            self.config['apids'].append(lst)

        self.config['tpid'] = cells[7]
        self.config['caid'] = cells[8]
        self.config['sid'] = cells[9]
        self.config['nid'] = cells[10]
        self.config['tid'] = cells[11]
        self.config['rid'] = cells[12]

        if self.config['frequency'] > 0:
            while self.config['frequency'] < 1000000:
                self.config['frequency'] *= 1000

        self.map_config( 'hierarchie', self.map_hierarchy )
        self.map_config( 'bandwidth', self.map_bandwidth )
        self.map_config( 'transmissionmode', self.map_bandwidth )
        self.map_config( 'guardinterval', self.map_guardinterval )
        self.map_config( 'modulation', self.map_modulation )
        self.map_config( 'dataratelow', self.map_fec )
        self.map_config( 'dataratehigh', self.map_fec )
        self.map_config( 'inversion', self.map_inversion )

            
    def map_config(self, key, keydict):
        if not self.config.has_key( key ):
            return   
        if self.config[ key ] in keydict.keys():
            self.config[ key ] = keydict[ self.config[ key ] ]
        else:
            log.warn('failed to parse %s (%s) - using default %s' % (key, self.config[key], keydict['default']))
            self.config[key] = keydict[ 'default' ]
            
 
    def __str__(self):
        return '%s channel: %s  (vpid=%s  apids=%s)\n' % (self.cfgtype,
                                                          self.config['name'].ljust(15),
                                                          self.config['vpid'],
                                                          self.config['apids'])



class DVBMultiplex:
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
        # TODO FIXME return value returns True if channel with channame was found and deleted otherwise False
        self.chanlist = filter(lambda chan: chan.config['name'] == channame, self.chanlist)
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


    def __str__(self):
        s = '\nMULTIPLEX: name=%s  (f=%s)\n' % (self.name.ljust(14), self.frequency)
        for chan in self.chanlist:
            s += str(chan)
        return s



class DVBChannelConfReader:
    def __init__(self, cfgname):
        self.cfgtype = None
        self.multiplexlist = [ ]

        # read config
        self.f = open(cfgname)
        for line in self.f:
            channel = DVBChannel(line)
            
            if self.cfgtype == None:
                self.cfgtype = channel.cfgtype
            else:
                if self.cfgtype is not channel.cfgtype:
                    log.warn('Oops: mixed mode config file! Dropping this line!\nline: %s' % line)
                    channel = None
                    
            if channel:
                for mplex in self.multiplexlist:
                    log.info('added channel %s to mplex %s' % (channel.config['name'], mplex.name))
                    added = mplex.add( channel )
                    if added:
                        break
                else:
                    mplex = DVBMultiplex( channel.config['frequency'], channel.config['frequency'], )
                    mplex.add( channel )
                    self.multiplexlist.append(mplex)
                    log.info('added channel %s to new mplex %s' % (channel.config['name'], mplex.name))


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
            if key in mplex:
                return mplex[key]

    def __str__(self):
        s = 'MULTIPLEX LIST:\n'
        s += '===============\n'
        for mplex in self.multiplexlist:
            s += str(mplex)
        return s
    

if __name__ == '__main__':
    ccr = DVBChannelConfReader('./dvb.conf')
    print ccr
