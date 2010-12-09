from kaa import imlib2, display, main

decorated = False
shaped = True

def redraw(regions):
    window.render_imlib2_image(image)

def button_pressed(pos, state, button, window_name):
    print 'Button Press:', pos, state, button, window_name

def button_released(pos, state, button, window_name):
    print 'Button Release:', pos, state, button, window_name


def key_pressed(key, window_name):
    print 'Key Press: ', key, window_name

def key_released(key, window_name):
    print 'Key Released: ', key, window_name
    if key in ('esc', 'q', 'Q'):
        main.stop()
    elif key in ('t','T'):
        if input_window.get_visible():
            input_window.hide()
        else:
            input_window.show()
    elif key in ('p', 'P'):
        if hasattr(input_window, 'proxy_for'):
            del input_window.proxy_for
        else:
            input_window.proxy_for = window


def mapped():
    window.focus()
    input_window.show()

window = display.X11Window(size = (800, 600), title = "Kaa Display Test")
input_window = display.X11Window(size=(800,600),input_only=True,parent=window)

imlib2.add_font_path("data")

image = imlib2.new((800,600))
image.clear()
image.draw_ellipse((400,300), (400, 300), (0,0,255,255))
image.draw_text((10, 50), "This is a Kaa Display X11Window Input Test", (255,255,255,255), "VeraBd/24")

window.signals['expose_event'].connect(redraw)
window.signals['key_press_event'].connect(key_pressed, 'window')
window.signals['key_release_event'].connect(key_released, 'window')
window.signals['button_press_event'].connect(button_pressed, 'window')
window.signals['button_release_event'].connect(button_released, 'window')
input_window.signals['key_press_event'].connect(key_pressed, 'input_window')
input_window.signals['key_release_event'].connect(key_released, 'input_window')
input_window.signals['button_press_event'].connect(button_pressed, 'input_window')
input_window.signals['button_release_event'].connect(button_released, 'input_window')
window.signals['map_event'].connect(mapped)

window.show()


print 'X11Window Input test app'
print 'Use the Esc or q key to Quit'
print 'Use the t key to show/hide the input window'
print 'Use the p key to toggle use of the proxy_for setting on the input window'
main.run()
