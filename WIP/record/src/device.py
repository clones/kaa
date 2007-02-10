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

class Device(object):
    """
    Basic device class defining the needed functions all devices need to
    provide. Override all the functions without calling this class.
    """
    def start_recording(self, channel, filter_chain):
        """
        Start recording the channel to the filter chain. This function needs
        to return a unique id for stopping the recording later.
        """
        raise RuntimeError('start_recording undefined')


    def stop_recording(self, id):
        """
        Stop the recording with the given id.
        """
        raise RuntimeError('stop_recording undefined')
