import math
import kaa
import kaa.candy

class Message(kaa.candy.LayoutGroup):

    def __init__(self, text, font, color, border, content=None, context=None):
        super(Message, self).__init__(layout='vertical', context=context)
        if kaa.candy.is_template(border):
            border = border()
        if kaa.candy.is_template(content):
            border = content()
        self.border = border
        self.border.passive = True
        self.border.parent = self
        self.spacing = 20
        self.text = kaa.candy.Text(None, None, text, font, color)
        self.text.parent = self
        self.text.yalign = self.ALIGN_SHRINK
        self.text.xalign = self.ALIGN_CENTER
        self.xalign = self.yalign = self.ALIGN_SHRINK
        self.content = content
        if content:
            self.content.xalign = self.content.ALIGN_CENTER
            self.content.parent = self

    def _clutter_message_create(self):
        """
        Create the widgets in the message popup
        """
        # We need at least text_height * text_width space for the text, in
        # most cases more (because of line breaks. To make the text look
        # nice, we try 4:3 aspect of the box at first and than use the max
        # height we can get. If you are wondering about the function
        # calculating w (using sqrt and such things), my math skills told
        # me to write that, it looks ok, don't mess with it :)
        text_width  = font.get_width(txt)
        text_height = int(font.get_height(2) * 1.2)
        min_width = self.parent.width / 3
        max_width = int(self.parent.width / 1.1)
        max_height = int(self.parent.height / 1.1)
        self.text.width = max(min(int(math.sqrt(text_height * text_width * 4 / 3)), max_width), min_width)
        self.text.height = max_height
        if self.content:
            self.content.width = self.text.width

    def _clutter_render(self):
        """
        Render the widget
        """
        if self._obj is None:
            self._clutter_message_create()
        super(Message, self)._clutter_render()
        if self.x == 0:
            self.x = max((self.parent.width - self.width) / 2, 0)
        if self.y == 0:
            self.y = max((self.parent.height - self.height) / 3, 0)


class Button(kaa.candy.Group):
    def __init__(self, text, font, color, box):
        super(Button, self).__init__(None, (200, 50))
        self.xpadding = 20
        box.parent = self
        box.passive = True
        label = kaa.candy.Label(None, None, font, color, text)
        label.parent = self
        label.xpadding = 20
        label.xalign = label.yalign = label.ALIGN_SHRINK
        self.xalign = self.yalign = label.ALIGN_SHRINK

# create a stage window
stage = kaa.candy.Stage((800,600))

font = kaa.candy.Font('vera:24')
txt = 'This is some text in a popup box'

# define the popup background as xml to get a template we can use for
# several boxes. Besides that, the code is smaller this way
box = stage.candyxml('''
    <container>
      <rectangle x="5" y="5" color="0x111111">
        <properties xpadding="-20" ypadding="-20"/>
      </rectangle>
      <rectangle color="0x444444">
        <properties xpadding="-10" ypadding="-10"/>
      </rectangle>
    </container>''')

# ############### empty popup ############### #
m = Message(txt, font, '0xffffff', box)
m.x = 50
m.y = 50
m.parent = stage

# ############### button popup ############### #

buttons = kaa.candy.LayoutGroup(layout='horizontal')
buttons.add(
    Button('OK', font, '0xffffff', kaa.candy.Rectangle(color='0x888888')),
    Button('Cancel', font, '0xffffff', kaa.candy.Rectangle(color='0x888888')))
buttons.yalign = buttons.ALIGN_SHRINK

m = Message(txt, font, '0xffffff', box, buttons)
m.x = 450
m.y = 50
m.parent = stage

# ############### progressbar popup ############### #

progressbar = kaa.candy.Group(size=(None, 20))
kaa.candy.Rectangle(color='0xaaaaaa').parent = progressbar
progress = kaa.candy.Progressbar(progress=kaa.candy.Rectangle(color='0xffffff'))
progress.max = 100
progress.progress = 30
progress.parent = progressbar

m = Message(txt, font, '0xffffff', box, progressbar)
m.x = 50
m.y = 350
m.parent = stage

# run the kaa mainloop, it takes some time to load all the images.
kaa.main.run()
