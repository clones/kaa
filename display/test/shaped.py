from kaa import imlib2, display, main

decorated = False
shaped = True

def redraw(regions):
    window.render_imlib2_image(image)

def key_pressed(key):
    key = key.lower()
    if key == 'esc' or key == 'q':
        main.stop()
    
    if key == 'd':
        global decorated
        decorated = not decorated
        window.hide()
        window.set_decorated(decorated)
        window.show()
    
    if key == 's':
        global shaped
        shaped = not shaped
        if shaped:
            window.set_shape_mask_from_imlib2_image(image, (0,0))
        else:
            window.reset_shape_mask()

def mapped():
    window.focus()

window = display.X11Window(size = (800, 600), title = "Kaa Display Test")

imlib2.add_font_path("data")

image = imlib2.new((800,600))
image.clear()
image.draw_ellipse((400,300), (400, 300), (0,0,255,255))
image.draw_text((10, 50), "This is a Kaa Display Shaped Window Test", (255,255,255,255), "VeraBd/24")

window.signals['expose_event'].connect(redraw)
window.signals['key_press_event'].connect(key_pressed)
window.signals['map_event'].connect(mapped)

window.set_decorated(decorated)
window.set_shape_mask_from_imlib2_image(image, (0,0))
window.show()


print 'Shaped window test app'
print 'Use the following keys to test features'
print 'Esc or q = Quit'
print 'd = Toggle Decorated'
print 's = Toggle shaped'
main.run()
