import sys
import logging
import kaa.popcorn
import kaa.display
    
# logging.getLogger('popcorn').setLevel(logging.DEBUG)

window = kaa.display.GladeWindow('gtkvideo.glade', 'window1')
video  = window.get_widget('video')
vidwin = kaa.display.GTKWindow(video.window)

player = kaa.popcorn.Player()
kaa.popcorn.config.preferred = 'mplayer'
player.set_window(vidwin)
player.open(sys.argv[1])
player.play()
kaa.main.run()
