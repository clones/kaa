import kaa.display._FBmodule as fb
import kaa.imlib2

class Framebuffer(object):
    def __init__(self):
        fb.open()
        self.image = kaa.imlib2.new(fb.size())

    def set_image(self, image):
        if (image.width, image.height) != fb.size():
            raise AttributeError('Invalid image size')
        self.image = image

    def size(self):
        return fb.size()

    def blend(self, src, src_pos = (0, 0), dst_pos = (0, 0)):
        self.image.blend(src, src_pos=src_pos, dst_pos=dst_pos)

    def update(self):
        fb.update(self.image._image)

    def __del__(self):
        fb.close()
