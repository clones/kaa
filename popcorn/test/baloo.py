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
import kaa.beacon
import kaa.popcorn

class Baloo(object):
    def __init__(self):
        gladefile = os.path.dirname(os.path.abspath(__file__)) + '/baloo.glade'
        self.xml = gtk.glade.XML(gladefile, 'baloo')
        dic = { "on_search_activate" : self.on_search_activate,
                "on_pause_clicked" : self.on_pause_clicked,
                "on_next_clicked" : self.on_next_clicked,
                "on_prev_clicked" : self.on_prev_clicked,
                "on_exit" : self.on_exit }
        self.xml.signal_autoconnect (dic)

        self.timer = kaa.Timer(self.update_timer)
        self.search = []
        self.current = None
        self.player = kaa.popcorn.Player()
        self.player.signals['end'].connect_weak(self.play_next)
        self.player.signals['pause'].connect_weak(self.player_pause)
        self.player.signals['play'].connect_weak(self.player_play)

        
    def update_playlist(self):
        if len(self.search):
            for t in ('pause', 'prev', 'next'):
                self.xml.get_widget(t).set_sensitive(True)
            return True

        for t in ('artist', 'album'):
            self.xml.get_widget(t).set_text('')
        self.xml.get_widget('title').set_text('<no match>')
        for t in ('pause', 'prev', 'next'):
            self.xml.get_widget(t).set_sensitive(False)
        if self.timer.active():
            self.timer.stop()
        return True
    
    @kaa.coroutine()
    def on_search_activate(self, data=None):
        string = self.xml.get_widget("search").get_text()
        self.search = yield kaa.beacon.query(type='audio', keywords=string)
        self.search.signals['changed'].connect(self.update_playlist)
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

    def on_prev_clicked(self, data=None):
        self.play_next(-1)

    def on_exit(self, data=None):
        sys.exit(0)

    def update_timer(self):
        secs = int(self.player.get_position())
        self.xml.get_widget('timer').set_text('%02d:%02d' % ((secs / 60), (secs % 60)))
        return True

    def play_next(self, offset = 1):
        try:
            index = self.search.index(self.current) + offset
            if index == len(self.search):
                index = 0
        except (KeyError, ValueError), e:
            index = 0
        self.current = None
        if not len(self.search):
            return False
        self.current = self.search[index]
        self.player.open(self.current.filename, player='xine')
        self.player.play()
        for t in ('title', 'artist', 'album'):
            label = self.xml.get_widget(t)
            value = self.current.get(t) or ''
            if t == 'title':
                value = "<b>%s</b>" % value
            label.set_markup(value)

        self.xml.get_widget('prev').set_sensitive(index > 0)
        self.xml.get_widget('next').set_sensitive(index < len(self.search)-1)
        self.xml.get_widget('count').set_text("%d of %d" % (index+1, len(self.search)))
 
    def player_pause(self):
        self.xml.get_widget('pause').set_label('gtk-media-play')

    def player_play(self):
        self.xml.get_widget('pause').set_label('gtk-media-pause')

baloo = Baloo()
kaa.main.run()
