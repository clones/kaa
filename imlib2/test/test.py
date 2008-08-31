#!/usr/bin/python
import kaa.imlib2

# FIXME: flesh this out.

img = kaa.imlib2.new((640, 480))
img.draw_ellipse((50, 50), (50, 50), (255, 0, 0))
assert(img.get_pixel((75, 75)) == (255, 0, 0, 255))
img2 = img.copy()
img2.blur(20)
img2.flip_horizontal()

img.blend(img2, alpha=100)
img.save('test.png')
