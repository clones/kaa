#!/usr/bin/python
#
# TODO FIXME add missing GPL header


import re
import sys

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

class Channel:
    # TODO / FIXME add missing compare function

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
            print 'FAILED TO PARSE CONFIG LINE:\n', self.line
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
                self.config['polarization'] = param[0]
            if param[0]=='V':
                self.config['polarization'] = param[0]
            if param[0]=='R':
                self.config['polarization'] = param[0]
            if param[0]=='L':
                self.config['polarization'] = param[0]

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

 
    def __str__(self):
        return '%s channel: %s  (vpid=%s  apids=%s)\n' % (self.cfgtype, self.config['name'].ljust(15), self.config['vpid'], self.config['apids'])



class Multiplex:
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


    def __str__(self):
        s = '\nMULTIPLEX: name=%s  (f=%s)\n' % (self.name.ljust(14), self.frequency)
        for chan in self.chanlist:
            s += str(chan)
        return s



class ChannelConfReader:
    def __init__(self, cfgname):
        self.cfgtype = None
        self.multiplexlist = [ ]

        # read config
        self.f = open(cfgname)
        for line in self.f:
            channel = Channel(line)
            
            if self.cfgtype == None:
                self.cfgtype = channel.cfgtype
            else:
#                print channel.cfgtype
#                print channel.config
                if self.cfgtype is not channel.cfgtype:
                    print 'Oops: mixed mode config file! Dropping this line!'
                    channel = None
                    
            if channel:
                for mplex in self.multiplexlist:
                    added = mplex.add( channel )
                    if added:
                        break
                else:
                    mplex = Multiplex( channel.config['frequency'], channel.config['frequency'], )
                    mplex.add( channel )
                    self.multiplexlist.append(mplex)


    def __str__(self):
        s = 'MULTIPLEX LIST:\n'
        s += '===============\n'
        for multiplex in self.multiplexlist:
            s += str(multiplex)
        return s
    

if __name__ == '__main__':
    ccr = ChannelConfReader('./dvbt.conf')
    print ccr
