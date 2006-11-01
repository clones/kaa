# -*- coding: iso-8859-1 -*-
# -----------------------------------------------------------------------------
# sdl.py - SDL window
# -----------------------------------------------------------------------------
# $Id$
#
# -----------------------------------------------------------------------------
# kaa.display - Generic Display Module
# Copyright (C) 2005, 2006 Dirk Meyer, Jason Tackaberry
#
# First Edition: Dirk Meyer <dmeyer@tzi.de>
# Maintainer:    Dirk Meyer <dmeyer@tzi.de>
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
import pygame
import pygame.locals
import time
import kaa.notifier

# the display module
import _X11

class PygameDisplay(object):
    def __init__(self, size):

        # Initialize the PyGame modules.
        if not pygame.display.get_init():
            pygame.display.init()
            pygame.font.init()

        # get screen with 32 bit
        self._screen = pygame.display.set_mode(size, 0, 32)
        if self._screen.get_bitsize() != 32:
            # if the bitsize is not 32 as requested, we need
            # a tmp surface to convert from imlib2 to pygame
            # because imlib2 uses 32 bit and with a different
            # value memcpy will do nasty things
            self._surface = pygame.Surface(size, 0, 32)
        else:
            self._surface = None
        # define signals
        self.signals = { 'key_press_event' : kaa.notifier.Signal(),
                         'mouse_up_event'  : kaa.notifier.Signal(),
                         'mouse_down_event': kaa.notifier.Signal() }
        # connect to idle loop
        kaa.notifier.signals['step'].connect(self.poll)
        # keyboard settings
        pygame.key.set_repeat(500, 30)
        # mouse settings
        self.hide_mouse = True
        self.mousehidetime = time.time()


    def render_imlib2_image(self, image, areas=None):
        """
        Render image to pygame surface. The image size must be the same size
        as the pygame window or it will crash. The optional parameter areas
        is a list of pos, size of the areas to update.
        """
        if self._surface:
            # we need to use our tmp surface
            _X11.image_to_surface(image, self._surface)
            if areas == None:
                # copy everything
                self._screen.blit(self._surface, (0,0))
            else:
                # copy only the needed areas
                for pos, size in areas:
                    self._screen.blit(self._surface, pos, pos + size)
        else:
            # copy everything
            _X11.image_to_surface(image, self._screen)

        # update the screen
        if areas:
            pygame.display.update(areas)
        else:
            pygame.display.update()


    def poll(self):
        """
        Pygame poll function to get events.
        """
        if not pygame.display.get_init():
            return True

        if self.hide_mouse:
            # Check if mouse should be visible or hidden
            mouserel = pygame.mouse.get_rel()
            mousedist = (mouserel[0]**2 + mouserel[1]**2) ** 0.5

            if mousedist > 4.0:
                pygame.mouse.set_visible(1)
                # Hide the mouse in 2s
                self.mousehidetime = time.time() + 1.0
            else:
                if time.time() > self.mousehidetime:
                    pygame.mouse.set_visible(0)

        # Signal the events
        while 1:
            event = pygame.event.poll()

            if event.type == pygame.locals.NOEVENT:
                return True

            if event.type == pygame.locals.KEYDOWN:
                self.signals["key_press_event"].emit(event.key)

            if event.type == pygame.locals.MOUSEBUTTONDOWN:
                self.signals["mouse_down_event"].emit(event.button, event.pos)

            if event.type == pygame.locals.MOUSEBUTTONUP:
                self.signals["mouse_up_event"].emit(event.button, event.pos)
