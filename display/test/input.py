from kaa import imlib2, display, main

decorated = False
shaped = True

def redraw(regions):
    window.render_imlib2_image(image)

def button_pressed(pos, state, button):
    print 'Button Press:', pos, state, button

def button_released(pos, state, button):
    print 'Button Release:', pos, state, button


def key_pressed(key):
    print 'Key Press: ', key

def key_released(key):
    print 'Key Released: ', key
    key = key.lower()
    if key == 'esc' or key == 'q':
        main.stop()


def mapped():
    window.focus()

window = display.X11Window(size = (800, 600), title = "Kaa Display Test")

imlib2.add_font_path("data")

image = imlib2.new((800,600))
image.clear()
image.draw_ellipse((400,300), (400, 300), (0,0,255,255))
image.draw_text((10, 50), "This is a Kaa Display X11Window Input Test", (255,255,255,255), "VeraBd/24")

window.signals['expose_event'].connect(redraw)
window.signals['key_press_event'].connect(key_pressed)
window.signals['key_release_event'].connect(key_released)
window.signals['button_press_event'].connect(button_pressed)
window.signals['button_release_event'].connect(button_released)

window.signals['map_event'].connect(mapped)

window.show()


print 'X11Window Input test app'
print 'Use the Esc or q key to Quit'
main.run()
