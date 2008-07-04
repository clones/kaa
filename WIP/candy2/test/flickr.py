import kaa
import kaa.candy
import feedparser

# before anything else, init kaa.candy
kaa.candy.init()

# we use the following xml (file) as gui. There are two main widgets:
# a label called "wait" and a container called "flickr" with a label and
# a grid in it. The grid needs a template for each cell which is again a
# container with a label and an image. The flickr container depends on
# two variables in the context: title for the label and items for the
# grid. The image also has a reflection modifier.
xml = '''
<candyxml geometry="800x600">
    <label name="wait" y="100" font="Vera:24" color="0xcccccc" align="center">
        Loading feed, please wait
    </label>
    <container name="flickr" x="10" y="10" width="780" height="580">
        <label font="Vera:24" color="0xcccccc" align="center">
            $title
        </label>
        <grid y="50" height="530" cell-width="140"
            cell-height="140" items="items" cell-item="item">
            <container>
                <image url="$item.thumbnail" height="100">
                    <reflection opacity="70"/>
                </image>
                <label y="110" font="Vera:10" color="0xcccccc" align="center">
                    $item.title
                </label>
            </container>
        </grid>
    </container>
</candyxml>
'''

# create a stage window and parse the xml file
stage = kaa.candy.Stage((800,600))
candy = stage.candyxml(xml)[1]

# add the wait widget to the stage. Since it is only a template it is
# safe to do this in the mainloop.
label = stage.add(candy.label.wait)

# now load a flickr RSS feed and create the context
class Image(object):
    def __init__(self, title, thumbnail):
        self.title = title
        self.thumbnail = thumbnail

feed = feedparser.parse('http://api.flickr.com/services/feeds/photos_public.gne?tags=beach&lang=en-us&format=atom')

items = []
for item in feed.entries:
    tmp = item.content[0]['value'][item.content[0]['value'].find('img src="')+9:]
    url = tmp[:tmp.find('"')]
    items.append(Image(item.title, url))

# this is the context for the flickr widget
context = dict(title=feed.feed.title, items=items)

# remove the wait label (it is safe to remove something from the stage in the
# mainloop) and add the flickr container based on the context
stage.remove(label)
stage.add(candy.container.flickr, context=context)

# run the kaa mainloop, it takes some time to load all the images.
kaa.main.run()
