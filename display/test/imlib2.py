from kaa import imlib2, display, main

window = display.X11Window(size = (800, 600), title = "Kaa Display Test")
image = imlib2.open("data/background.jpg")
imlib2.add_font_path("data")
image.draw_text((50, 50), "This is a Kaa Display Imlib2 Test", (255,255,255,255), "VeraBd/24")
window.show()
window.render_imlib2_image(image)
main()
