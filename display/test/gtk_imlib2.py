import gtk

import kaa
import kaa.imlib2
import kaa.display


window = gtk.Window()
window.set_size_request(1024, 768)

da = gtk.DrawingArea()
da.set_size_request(800, 600)
    
window.add(da)
window.connect("destroy", gtk.main_quit)
window.show_all()
    
image = kaa.imlib2.open("data/background.jpg")

# print da.window.xid

sock = gtk.Socket()
sock.add_id(da.window.xid)

x11win = kaa.display.X11Window(window = sock.get_id())
# x11win.render_imlib2_image(da.image)

kaa.main.run()

