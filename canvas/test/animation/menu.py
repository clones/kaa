from kaa import canvas
import kaa

menu_items = []        # List of Text objects for menu items
watermark_items = []   # List of Image objects for watermarks
cur_item = 0           # Current menu item index


def handle_key(key):
    new_item = cur_item
    if key == "q":
        raise SystemExit
    elif key == "down":
        new_item = min(len(menu_items)-1, cur_item + 1)
    elif key == "up":
        new_item = max(0, cur_item - 1)
    if new_item != cur_item:
        set_menu_item(new_item)


def set_menu_item(new_item):
    global cur_item
    if cur_item != new_item:
        # Fade old item out
        watermark_items[cur_item].animate("color", a=0, duration = 0.2)
        # Shrink old item to 20% size as it fades out.
        watermark_items[cur_item].animate("size", width="20%", duration = 0.2)
    # Fade new item in (to alpha = 150)
    watermark_items[new_item].animate("color", a=150, duration = 0.2)
    # Grow new item to 30% size as it's fading in.
    watermark_items[new_item].animate("size", width="30%", duration = 0.2, 
                                      bounce = True, bounce_factor = 0.3)
    cur_item = new_item

    # Move the menu item selector to the new position, decelerating as it
    # approaches its new position.  It will also bounce a little bit.
    pos = menu_items[cur_item]._get_relative_values("pos")
    selector.animate("move", left=pos[0] - 10, top=pos[1] - 5, duration = 0.1, 
                     bounce = True, decelerate = True)


def menu_reflow():
    """
    Called when the menu box has reflowed (i.e. any of its children have
    resized/moved, or when the box itself has moved again.  We need to
    update the menu item selector to reflect the new position.
    """
    item = menu_items[cur_item]
    size = item.get_computed_size()
    pos = item._get_relative_values("pos")
    selector.resize(200, size[1] + 10)
    selector.move(pos[0] - 10, pos[1] - 5)
    set_menu_item(cur_item)


# If you have a GL capable card, set use_gl=True for smoother performance.
c = canvas.X11Canvas((640,480), use_gl=False)
c.add_child(kaa.canvas.Image("royale/background.jpg"), width="100%", height="100%")


# Create the watermark images for each of the menu items.
for item in ("tv", "videos", "music", "photos", "dvd", "settings"):
    img = c.add_child(canvas.Image("royale/mainmenu_watermark_%s.png" % item))
    img.move(vcenter="40%", hcenter = "60%")
    # Initialize these images to 20% size and alpha=0 (invisible)
    img.set_width("20%")
    img.set_color(a = 0)
    watermark_items.append(img)

# Load the menu item selector image.
selector = c.add_child(kaa.canvas.Image("royale/list_selector.png"))
# Set the border to 10 pixels in all directions, so that scaling the selector
# won't distort its edges.
selector.set_border(10, 10, 10, 10)
# Slightly transparent, so we can see the watermarks through the selector.
selector.set_color(a = 200)

# Now create the text items for the menu.
menu = c.add_child(canvas.VBox(), vcenter="50%", left="20%", width = 180)
for item in ("Television", "Videos", "Music", "Photos", "Play DVD", "Settings"):
    # If you don't have Trebuchet installed, change this font name.
    # Offset the item 15 pixels from the top (gives each item a bit of 
    # padding)
    menu_items.append(menu.add_child(canvas.Text(item, font="trebuc"), top=15))

# We want to know when the menu item changes position or size, so we can
# update the selector image.
menu.signals["reflowed"].connect(menu_reflow)
menu.signals["moved"].connect(lambda old, new: menu_reflow())

# Allow key presses both in console and on the window.
kaa.signals["stdin_key_press_event"].connect(handle_key)
c.signals["key_press_event"].connect(handle_key)

kaa.base.create_logger()

print "Use up/down arrows; q to quit."
kaa.main()

