# -*- coding: iso-8859-1 -*-
# -----------------------------------------------------------------------------
# source_vdr.py - Get EPG information from VDR.
# -----------------------------------------------------------------------------
# $Id: $
#
# -----------------------------------------------------------------------------
# kaa-epg - Python EPG module
# Copyright (C) 2002-2005 Dirk Meyer, Rob Shortt, et al.
#
# First Edition: Rob Shortt <rob@tvcentric.com>
# Maintainer:    Rob Shortt <rob@tvcentric.com>
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
import string
import logging

# kaa imports
from kaa import strutils
import kaa.notifier
from kaa.config import Var, Group

# vdr imports
from vdr.vdr import VDR

# get logging object
log = logging.getLogger('epg')


# Source configuration
config = \
       Group(name='vdr', desc=u'''
       VDR settings
       
       Add more doc here please!
       ''',
             desc_type='group',
             schema = [

    Var(name='activate',
        default=False,
        desc=u'Use VDR to populate the database.'),

    Var(name='dir',
        default='/video',
        desc=u'VDR main directory.'),

    Var(name='channels_file',
        default='channels.conf',
        desc=u'VDR channels file name.'),
    
    Var(name='epg_file',
        default='epg.data',
        desc=u'VDR EPG file name.'
       ),

    Var(name='host',
        default='localhost',
        desc=u'VDR SVDRP host.'
       ),
    
    Var(name='port',
        default=2001,
        desc=u'VDR SVDRP port.'
       ),

    Var(name='access_by',
        type=('name', 'sid' 'rid'),
        default='sid',
        desc=u'Which field to access channels by: name, sid (service id), \n'+
        u'or rid (radio id).'
       ),

    Var(name='limit_channels',
        type=('epg', 'chan' 'both'),
        default='chan',
        desc=u'Limit channels added to those found in the EPG file, the \n'+
        u'channels file, or both.  Values: epg, chan, both'
       ),
    ])


class UpdateInfo:
    pass

def _update_data_thread(epg, vdr_dir=None, channels_file=None, epg_file=None,
                        host=None, port=None, access_by='sid', 
                        limit_channels='conf', exclude_channels=None):
    """
    Update the guide.
    """
    log.debug('_update_data_thread')

    info = UpdateInfo()
    info.total = 0

    if not (isinstance(exclude_channels, list) or \
            isinstance(exclude_channels, tuple)):
        exclude_channels = []

    log.info('excluding channels: %s' % exclude_channels)

    info.vdr = VDR(host=host, port=port, videopath=vdr_dir,
                   channelsfile=channels_file, epgfile=epg_file,
                   close_connection=0)

    if info.vdr.epgfile and os.path.isfile(info.vdr.epgfile):
        log.info('Using VDR EPG from %s.' % info.vdr.epgfile)
        if os.path.isfile(info.vdr.channelsfile):
            info.vdr.readchannels()
        else:
            log.warning('VDR channels file not found: %s.' % info.vdr.channelsfile)
        info.vdr.readepg()
    elif info.vdr.host and info.vdr.port:
        log.info('Using VDR EPG from %s:%s.' % (info.vdr.host, info.vdr.port))
        info.vdr.retrievechannels()
        info.vdr.retrieveepg()
    else:
        log.info('No source for VDR EPG.')
        return False

    for c in info.vdr.channels.values():
        for e in c.events:
            info.total += 1

    info.access_by        = access_by
    info.limit_channels   = limit_channels
    info.exclude_channels = exclude_channels
    info.cur              = 0
    info.epg              = epg
    info.progress_step    = info.total / 100

    timer = kaa.notifier.Timer(_update_process_step, info)
    timer.set_prevent_recursion()
    timer.start(0)


def _update_process_step(info):

    chans = info.vdr.channels.values()
    for c in chans:
        if c.id in info.exclude_channels:  continue

        if string.lower(info.limit_channels) == 'epg' and not c.in_epg:
            continue
        elif string.lower(info.limit_channels) == 'conf' and not c.in_conf:
            continue
        elif string.lower(info.limit_channels) == 'both' and \
                 not (c.in_conf and c.in_epg):
            continue

        if info.access_by == 'name':
            access_id = c.name
        elif info.access_by == 'rid':
            access_id = c.rid
        else:
            access_id = c.sid

        log.info('Adding channel: %s as %s' % (c.id, access_id))

        chan_db_id = info.epg._add_channel_to_db(tuner_id=strutils.str_to_unicode(access_id), 
                                                 name=strutils.str_to_unicode(c.name), 
                                                 long_name=None)

        for e in c.events:
            subtitle = e.subtitle
            if not subtitle:
                subtitle = ''
            desc = e.desc
            if not desc:
                desc = ''

            info.epg._add_program_to_db(chan_db_id, e.start, int(e.start+e.dur),
                                        strutils.str_to_unicode(e.title),
                                        desc=strutils.str_to_unicode(desc))

            info.cur +=1
            if info.cur % info.progress_step == 0:
                info.epg.signals["update_progress"].emit(info.cur, info.total)

    info.epg.signals["update_progress"].emit(info.cur, info.total)
    return False


def update(epg, vdr_dir=None, channels_file=None, epg_file=None,
           host=None, port=None, access_by='sid', limit_channels=''):
    log.debug('update')

    thread = kaa.notifier.Thread(_update_data_thread, epg, vdr_dir, 
                                 channels_file, epg_file, host, port, access_by,
                                 limit_channels)
    thread.start()

