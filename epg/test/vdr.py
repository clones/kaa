# -*- coding: iso-8859-1 -*-
# -----------------------------------------------------------------------------
# source_vdr.py - Get EPG information from VDR.
# -----------------------------------------------------------------------------
# $Id$
#
# -----------------------------------------------------------------------------
# kaa.epg - EPG Database
# Copyright (C) 2004-2006 Jason Tackaberry, Dirk Meyer, Rob Shortt
#
# First Edition: Rob Shortt <rob@tvcentric.com>
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

# python imports
import os
import string
import logging

# kaa imports
from kaa import strutils
import kaa
from kaa.config import Var, Group
from config_vdr import config

# vdr imports
from vdr.vdr import VDR

# get logging object
log = logging.getLogger('epg')


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
    info.epg              = epg
    info.progress_step    = info.total / 100

    timer = kaa.Timer(_update_process_step, info)
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

        chan_db_id = info.epg.add_channel(tuner_id=strutils.str_to_unicode(access_id),
                                          name=strutils.str_to_unicode(c.name),
                                          long_name=None)

        for e in c.events:
            subtitle = e.subtitle
            if not subtitle:
                subtitle = ''
            desc = e.desc
            if not desc:
                desc = ''

            info.epg.add_program(chan_db_id, e.start, int(e.start+e.dur),
                                 strutils.str_to_unicode(e.title),
                                 desc=strutils.str_to_unicode(desc))
    return False


def update(epg, vdr_dir=None, channels_file=None, epg_file=None,
           host=None, port=None, access_by='sid', limit_channels=''):
    log.debug('update')

    thread = kaa.Thread(_update_data_thread, epg, vdr_dir,
                                 channels_file, epg_file, host, port, access_by,
                                 limit_channels)
    thread.start()

