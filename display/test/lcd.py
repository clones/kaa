# -*- coding: iso-8859-1 -*-
import kaa.display
import kaa

screen = None

def g2():
    global screen
    screen = lcd.create_screen('t2')
    screen.widget_add('string', 1, 1, 'jjjjjjjjjjjjj')
    
def go(w, h):
    global screen
    screen = lcd.create_screen('test')
    screen.widget_add('string', 1, 1, 'hiä')
    kaa.OneShotTimer(g2).start(2)
    
lcd = kaa.display.LCD()
lcd.signals['connected'].connect(go)

kaa.main.run()
