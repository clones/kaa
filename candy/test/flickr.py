import kaa
import kaa.candy
import feedparser

# we use the following xml (file) as gui. There are two main widgets:
# a label called "wait" and a container called "flickr" with a label and
# a grid in it. The grid needs a template for each cell which is again a
# container with a label and an image. The flickr container depends on
# two variables in the context: title for the label and items for the
# grid. The image also has a reflection modifier.
# Note: this reflection is the reason why the scrolling is not smooth
# because we render in software. Remove that line for a better result.
xml = '''
<candyxml geometry="800x600">
    <label name="wait" y="100" font="Vera:24" color="0xcccccc">
        <properties xalign="center"/>
        Loading feed, please wait
    </label>
    <container name="flickr" x="10" y="10" width="780" height="580">
        <label font="Vera:24" color="0xcccccc">
            <properties xalign="center"/>
            $title
        </label>
        <grid y="50" height="530" cell-width="160" cell-height="140"
            items="items" cell-item="item" orientation="vertical">
            <properties name="items"/>
            <container>
                <image url="$item.thumbnail" width="160" height="100">
                    <properties xalign="center" yalign="center" keep-aspect="true"/>
                    <reflection opacity="80"/>
                </image>
                <label y="110" font="Vera:10" color="0xcccccc">
                    <properties xalign="center"/>
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
label = candy.label.wait()
stage.add(label)

# now load a flickr RSS feed and create the context
class Image(object):
    def __init__(self, title, thumbnail):
        self.title = title
        self.thumbnail = thumbnail

@kaa.threaded()
def load_feed(tag):
    feed = feedparser.parse('http://api.flickr.com/services/feeds/photos_public.gne?' +
                            'tags=%s&lang=en-us&format=atom' % tag)

    items = []
    num = 0
    for item in feed.entries:
        tmp = item.content[0]['value'][item.content[0]['value'].find('img src="')+9:]
        url = tmp[:tmp.find('"')]
        items.append(Image('%s' % num, url))
        num += 1
    return feed, items


@kaa.coroutine()
def main():
    feed, items = yield load_feed('beach')

    # this is the context for the flickr widget
    context = dict(title=feed.feed.title, items=items)

    # remove the wait label (it is safe to remove something from the stage in the
    # mainloop) and add the flickr container based on the context.
    stage.remove(label)
    container = candy.container.flickr(context=context)
    stage.add(container)

    print 'take a look'
    yield kaa.delay(1)
    print 'scroll down'
    grid = container.get_widget('items')
    grid.scroll_by((0, 2), 1)
    yield kaa.delay(2)
    print 'scroll right'
    grid.scroll_by((2, 0), 4)
    yield kaa.delay(2)
    print 'scroll up very fast, more than possible'
    grid.scroll_by((0,-15), 0.5)
    yield kaa.delay(2)
    print 'and down again'
    grid.scroll_by((1,1), 0.8)
    yield kaa.delay(0.7)
    print 'and left again while the animation is still running'
    grid.scroll_by((-1, 0), 0.8)
    yield kaa.delay(2)
    print 'go home (0,0)'
    grid.scroll_to((0, 0), 0.8)
    yield kaa.delay(2)
    print 'load more'

    # create new context and replace it
    feed, items = yield load_feed('sunset')
    context = dict(title=feed.feed.title, items=items)
    # set context
    container.context = context

main()

# run the kaa mainloop, it takes some time to load all the images.
kaa.main.run()
