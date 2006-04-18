#!/usr/bin/env python

import os
import sys

# GTK import. It is important to import gtk before kaa so that
# kaa can detect it and switch to the gtk notifier wrapper from
# pynotifier

import pygtk
pygtk.require('2.0')
import gtk
import gtk.glade

# now import kaa
import kaa
import kaa.notifier
import kaa.beacon
import kaa.player

class Baloo(object):
    def __init__(self):
        gladefile = os.path.dirname(os.path.abspath(__file__)) + '/baloo.glade'
        self.xml = gtk.glade.XML(gladefile, 'baloo')
        dic = { "on_search_activate" : self.on_search_activate,
                "on_pause_clicked" : self.on_pause_clicked,
                "on_next_clicked" : self.on_next_clicked,
                "on_exit" : self.on_exit }
        self.xml.signal_autoconnect (dic)

        self.timer = kaa.notifier.Timer(self.update_timer)
        self.search = []
        self.current = None
        self.player = kaa.player.Player()
        self.player.signals['end'].connect(self.play_next)

        
    def update_playlist(self):
        if len(self.search):
            return True
        for t in ('artist', 'album'):
            self.xml.get_widget(t).set_text('')
        self.xml.get_widget('title').set_text('<no match>')
        if self.timer.active():
            self.timer.stop()
        return True
    
    def on_search_activate(self, data=None):
        string = self.xml.get_widget("search").get_text()
        self.search = kaa.beacon.query(type='audio', keywords=string)
        self.search.monitor()
        self.update_playlist()
        if self.current:
            self.player.stop()
        else:
            self.play_next()
        if not self.timer.active():
            self.timer.start(0.1)
        
    def on_pause_clicked(self, data=None):
        if not len(self.search):
            return
        self.player.pause_toggle()
                
    def on_next_clicked(self, data=None):
        self.player.stop()

    def on_exit(self, data=None):
        sys.exit(0)

    def update_timer(self):
        secs = int(self.player.get_position())
        self.xml.get_widget('timer').set_text('%02d:%02d' % ((secs / 60), (secs % 60)))
        return True

    def play_next(self):
        try:
            index = self.search.index(self.current) + 1
            if index == len(self.search):
                index = 0
        except (KeyError, ValueError), e:
            index = 0
        self.current = None
        if not len(self.search):
            return False
        self.current = self.search[index]
        self.player.open(self.current.filename)
        self.player.play(video=False)
        for t in ('title', 'artist', 'album'):
            label = self.xml.get_widget(t)
            value = self.current.getattr(t) or ''
            label.set_text(value)
            
baloo = Baloo()
kaa.main()
