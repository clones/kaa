import os
import sys
import kaa.metadata
import kaa.display

SIZE = int(sys.argv[1]), int(sys.argv[2])

window = kaa.display.X11Window(size = SIZE, title = "kaa.popcorn")
window.show()

def scale(video_width, video_height, window_width, window_height,
          video_aspect=None, window_aspect=None):
    """
    Scale the video to fit the window and respect the given aspects.
    """
    if not video_aspect:
        video_aspect = float(video_width) / video_height
    if not window_aspect:
        window_aspect = float(window_width) / window_height

    scaling = float(window_aspect * window_height) / float(window_width)

    # correct video width by aspect
    video_width = float(video_aspect * video_height)

    s1 = (float(window_width) / video_width)
    s2 = (float(window_height) / video_height)

    width = int((video_width * max(s1, s2)) / scaling)
    height = int(video_height * max(s1, s2))

    if width > window_width + 1:
        # Oops, need different way to scale
        # Note: + 1 because of some possible internal errors
        width = int(video_width * min(s1, s2))
        height = int(video_height * min(s1, s2) * scaling)

    # adjust width and height if off by one
    if width + 1 == window_width or width -1 == window_width:
        width = window_width
    if height + 1 == window_height or height -1 == window_height:
        height = window_height
    return width, height

    
data = kaa.metadata.parse(sys.argv[3])
video_width = data.video[0]['width']
video_height = data.video[0]['height']
video_aspect = None
# video_aspect = float(16) / 9

window_width, window_height = window.get_size()
window_aspect = None
window_aspect = float(16) / 9

s =  scale(video_width, video_height, window_width, window_height,
           video_aspect, window_aspect)

filter = 'scale=%s:%s,expand=%s:%s' % (s[0], s[1], window_width, window_height)
cmd = 'mplayer -wid %s -vf %s "%s"' % (hex(window.get_id()), filter, sys.argv[3])
print cmd
os.system(cmd)

