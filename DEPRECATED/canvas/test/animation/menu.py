from kaa import canvas, input
import kaa.input.stdin
import kaa, sys


# 1 = all menu items are visible, scrolls as if it were a list.
# 2 = works like an option list.
MENU_STYLE = 1
if len(sys.argv) > 1 and sys.argv[1].isdigit():
    MENU_STYLE = max(1, min(2, int(sys.argv[1]))) 

menu_items = []        # List of Text objects for menu items
watermark_items = []   # List of Image objects for watermarks
cur_item = 0           # Current menu item index


def handle_lirc_event(code):
    lirc_map = { "exit": "q", "select": "enter", "down": "down", "up": "up" }
    code = code.lower()
    if code in lirc_map:
        handle_key(lirc_map[code])

def handle_key(key):
    new_item = cur_item
    if key == "q":
        raise SystemExit
    elif key == "down":
        new_item = min(len(menu_items)-1, cur_item + 1)
    elif key == "up":
        new_item = max(0, cur_item - 1)
    elif key == "enter":
        streak.move(right = 0)
        streak.animate("move", left="100%", duration = 0.25)
    elif key == "f":
        c.get_window().set_fullscreen(not c.get_window().get_fullscreen())

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
    section_text.set_text(menu_items[cur_item].get_text())

    # Move the menu item selector to the new position, decelerating as it
    # approaches its new position.  It will also bounce a little bit.
    if MENU_STYLE == 1:
        pos = menu_items[cur_item]._get_relative_values("pos")
        selector_box.animate("move", left=pos[0] - 10, top=pos[1] - 5, duration = 0.1, 
                             bounce = True, decelerate = True)
    elif MENU_STYLE == 2:
        pos = menu.get_child_position(menu_items[cur_item])
        menu.animate("move", top = -pos[1], duration = 0.3, bounce = True, decelerate = True, bounce_factor = 0.2)


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
    selector_box.resize(200, size[1] + 10)
    streak.resize(height = size[1] + 10)
    if MENU_STYLE == 1:
        selector_box.move(pos[0] - 10, pos[1] - 5)
    elif MENU_STYLE == 2:
        menu_box.resize(height = size[1])
    set_menu_item(cur_item)


# If you have a GL capable card, set use_gl=True for smoother performance.
c = canvas.X11Canvas((640,480), use_gl=None)
bg = c.add_child(kaa.canvas.Image("royale/background.jpg"), width="100%", height="100%")

marquee_box = c.add_child(canvas.Container(), width="100%")
title_text = marquee_box.add_child(canvas.Text("Kaa Demo", "../data/Vera", 92), right="100%")
section_text = marquee_box.add_child(canvas.Text(font="../data/Vera", size=72), vcenter="50%")

def start_animate_title_text():
    title_text.set_color(a = 80)
    title_text.move(left = "100%")
    title_text.animate("move", left="30%", duration=17, end_callback = start_animate_title_text)
    title_text.animate("color", a=0, duration=17)

def start_animate_section_text():
    section_text.set_color(a = 80)
    section_text.move(right = 0)
    section_text.animate("move", right="70%", duration=13, end_callback = start_animate_section_text)
    section_text.animate("color", a=0, duration=13)

start_animate_title_text()
start_animate_section_text()

# Create the watermark images for each of the menu items.
for item in ("tv", "videos", "music", "photos", "dvd", "settings"):
    img = c.add_child(canvas.Image("royale/mainmenu_watermark_%s.png" % item))
    img.move(vcenter="40%", hcenter = "60%")
    # Initialize these images to 20% size and alpha=0 (invisible)
    img.set_width("20%")
    img.set_color(a = 0)
    #img.set_margin(left=80)
    watermark_items.append(img)

selector_box = c.add_child(kaa.canvas.Container(), width = 200, clip = "auto")
# Load the menu item selector animation.
selector = selector_box.add_child(kaa.canvas.Image("royale/list_selector.png"))
# Set the border to 10 pixels in all directions, so that scaling the selector
# won't distort its edges.
selector.set_border(7, 7, 7, 7)
# Slightly transparent, so we can see the watermarks through the selector.
selector.set_color(a = 200)


streak = selector_box.add_child(kaa.canvas.Image("royale/list_selector_streak.png"), 
                                vcenter="50%", right=0, color=(255,255,255,160))

# Now create the text items for the menu.
menu_box = kaa.canvas.Container()
if MENU_STYLE == 1:
    c.add_child(menu_box, vcenter = "50%", left = "20%")
elif MENU_STYLE == 2:
    selector_box.move(hcenter = "40%", vcenter = "30%")
    selector_box.add_child(menu_box, left = 10, top = 5, clip = "auto")

menu = menu_box.add_child(canvas.VBox(), width = 180)
offset = (15, 5)[MENU_STYLE-1]
for item in ("Television", "Videos", "Music", "Photos", "Play DVD", "Settings"):
    # If you don't have Trebuchet installed, change this font name.
    # Offset the item 15 pixels from the top (gives each item a bit of 
    # padding)
    menu_items.append(menu.add_child(canvas.Text(item, font="../data/Vera"), top=offset))

# We want to know when the menu item changes position or size, so we can
# update the selector image.
menu.signals["reflowed"].connect(menu_reflow)
#menu.signals["moved"].connect(lambda old, new: menu_reflow())

# Allow key presses both in console and on the window.
kaa.signals["stdin_key_press_event"].connect(handle_key)
c.signals["key_press_event"].connect(handle_key)
if input.lirc.init():
    kaa.signals["lirc"].connect_weak(handle_lirc_event)


print "Use up/down arrows; enter selects; q to quit."
kaa.main.run()
#del c, menu, menu_box, selector, selector_box, streak, menu_items, watermark_items, img
