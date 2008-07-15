# Usage: test/beacon.py path-to-imagedir
# Note: kaa.beacon daemon must be running
import sys
import os

import kaa
import kaa.candy
import feedparser
import kaa.beacon

# before anything else, init kaa.candy
kaa.candy.init()

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
        <grid y="50" height="530" cell-width="160" cell-height="140"
            items="items" cell-item="item" orientation="vertical">
            <properties name="items"/>
            <container>
                <thumbnail thumbnail="item" height="100">
                    <reflection opacity="80"/>
                </thumbnail>
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

@kaa.coroutine()
def main():
    query = (yield kaa.beacon.get(sys.argv[1])).list()
    yield query.wait()
    
    # this is the context for the images widget
    context = dict(title=os.path.basename(sys.argv[1]), items=query)
    stage.add(candy.container.thumbnails, context=context)
    
main()

# run the kaa mainloop, it takes some time to load all the images.
kaa.main.run()
