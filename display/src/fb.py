import kaa.display._FBmodule as fb
import kaa.imlib2

# modelines for tv out
PAL_768x576  = (768, 576, 768, 576, 0, 0, 0, 0, 38400, 20, 10, 30, 10, 10, 34, 19, 0)
PAL_800x600  = (800, 600, 800, 600, 0, 0, 0, 0, 38400, 48, 24, 70, 32, 2, 40, 19, 0)
NTSC_640x480 = (640, 480, 640, 480, 0, 0, 0, 0, 35000, 36, 6, 22, 22, 1, 46, 0, 0)
NTSC_768x576 = (768, 576, 768, 576, 0, 0, 0, 0, 35000, 36, 6, 39, 10, 4, 46, 0, 0)
NTSC_800x600 = (800, 600, 800, 600, 0, 0, 0, 0, 39721, 48, 24, 80, 32, 2, 40, 1, 0)

class Framebuffer(object):
    def __init__(self, fbset=None):
        if fbset:
            fb.open(fbset)
        else:
            fb.open()
        self.image = kaa.imlib2.new(fb.size())

    def set_image(self, image):
        if (image.width, image.height) != fb.size():
            raise AttributeError('Invalid image size')
        self.image = image

    def info(self):
        return fb.info()
    
    def size(self):
        return fb.size()

    def blend(self, src, src_pos = (0, 0), dst_pos = (0, 0)):
        self.image.blend(src, src_pos=src_pos, dst_pos=dst_pos)

    def update(self):
        fb.update(self.image._image)

    def __del__(self):
        print 'foo'
        fb.close()
