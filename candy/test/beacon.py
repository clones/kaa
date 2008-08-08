# Usage: test/beacon.py path-to-imagedir
# Note: kaa.beacon daemon must be running
import sys
import os

import kaa
import kaa.candy
import feedparser
import kaa.beacon

# we use the following xml (file) as gui. There is one widget:
# a container called "thumbnails" with a label and a grid in it.
# The grid needs a template for each cell which is again a
# container with a label and an image.
xml = '''
<candyxml geometry="800x600">
    <container name="thumbnails" x="10" y="10" width="780" height="580">
        <label font="Vera:24" color="0xcccccc" align="center">
            $title
        </label>
        <grid style="selection" y="50" height="530" cell-width="120" cell-height="80"
            items="items" cell-item="item" orientation="vertical">
            <properties name="items"/>
            <thumbnail thumbnail="item"/>
            <selection>
                <rectangle color="0x6666cc" width="126" height="86"/>
            </selection>
        </grid>
    </container>
</candyxml>
'''

# create a stage window and parse the xml file
stage = kaa.candy.Stage((800,600))
candy = stage.candyxml(xml)[1]

def wait(secs):
    # maybe move that into kaa.notifier
    wait = kaa.InProgressCallback()
    kaa.OneShotTimer(wait).start(secs)
    return wait

@kaa.coroutine()
def main():
    query = (yield kaa.beacon.get(sys.argv[1])).list()
    yield query.wait()

    # this is the context for the images widget
    context = dict(title=os.path.basename(sys.argv[1]), items=query)
    container = stage.add(candy.container.thumbnails, context=context)
    grid = container.get_element('items')

    if 1:
        # add effects and hide selection rectangle
        grid.behave('opacity', 80, 255).behave('scale', (1, 1), (1.1, 1.1))
        grid.selection.opacity = 0
    if 0:
        # add effects and hide selection rectangle
        grid.behave('scale', (1, 1), (1.5, 1.5))

    yield wait(0.5)

    # now we move the selection
    print 'move selection to the right'
    grid.select((2, 0), 1)
    yield wait(1.5)

    print 'move selection down'
    grid.select((2, 2), 1)
    yield wait(1.5)

    print 'move selection down and scroll at the same time to make it look'
    print 'like the selection is standing still.'
    grid.select((2, 4), 1)
    grid.scroll_by((0, 2), 1)
    yield wait(1.5)
    print 'move selection down fast'
    grid.select((2, 5), 0.3)
    yield wait(1.5)
    print 'move selection and start scrolling with a different speed'
    grid.select((5, 5), 1)
    yield wait(0.3)
    grid.scroll_by((4, 0), 4)
    yield wait(2)
    grid.select((5, 3), 1)
    yield wait(2)
    print 'move selection very slowly'
    grid.select((7, 3), 3)
    yield wait(3.5)
    print 'scroll to get selection to the left side'
    grid.scroll_by((3, 0), 1)
    yield wait(2)
    print 'move selection fast to the right'
    grid.select((12, 3), 0.8)

main()

# run the kaa mainloop, it takes some time to load all the images.
kaa.main.run()
