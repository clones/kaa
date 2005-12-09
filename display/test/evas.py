from kaa import display, main
import gc

def handle_key(key, obj):
    alpha = obj.color_get()[3]
    if key == "down":
        obj.color_set(a = alpha - 10)
        obj.evas_get().render()
    elif key == "up":
        obj.color_set(a = alpha + 10)
        obj.evas_get().render()
    elif key == "q":
        raise SystemExit
    elif key == "t":
        canvas.viewport_set((0, 0), (720, 480))
        canvas.output_size_set((800, 600))
        obj.evas_get().render()
        

window = display.EvasX11Window(gl = False, size = (1024, 768), title = "Kaa Display Test")
window.set_cursor_hide_timeout(1)
canvas = window.get_evas()
canvas.viewport_set((0, 0), (800, 600))
canvas.output_size_set((1024, 768))
bg = canvas.object_image_add("data/background.jpg")
bg.show()

canvas.fontpath.append("data")
text = canvas.object_text_add(("VeraBd", 32), "This is a Kaa Display Evas Test")
text.move((50, 50))
text.show()

window.signals["key_press_event"].connect(handle_key, text)
window.show()

print "Up/down arrows modify text alpha level; 'q' quits."
main()
del window, canvas, bg, text
