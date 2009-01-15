#!/usr/bin/env python

# GTK import. It is important to import gtk before kaa so that kaa can
# detect it and switch to the gtk wrapper from pynotifier

import pygtk
pygtk.require('2.0')
import gtk

# now import kaa
import kaa
import kaa.beacon


class BeaconSearch:

    def __init__(self):
        self.search = None
        self._create_window()


    def _create_window(self):
        """
        Create window and other gui stuff.
        """
        # Create a new window
        self.window = gtk.Window(gtk.WINDOW_TOPLEVEL)
        self.window.set_title("Beacon Search")
        self.window.set_size_request(300, 600)

        self.window.connect("delete_event", self.delete_event)
        self.window.connect("destroy", self.destroy)

        # Sets the border width of the window.
        self.window.set_border_width(0)

        # Create VBox
        self.box = gtk.VBox(False, 0)
        self.window.add(self.box)

        # Create Search field
        entry = gtk.Entry()
        entry.set_max_length(50)
        entry.connect("activate", self.enter_callback, entry)
   
        self.button = gtk.Button("search")
        self.button.connect("clicked", self.enter_callback, entry)

        search = gtk.HBox(False, 0)
        search.pack_start(entry, True, True, 0)
        search.pack_start(self.button, False, False, 0)

        self.box.pack_start(search, False, False, 0)

        # create a liststore with one string column to use as the model
        self.liststore = gtk.ListStore(bool, str, str, str)

        # create the TreeView using liststore
        self.treeview = gtk.TreeView(self.liststore)

        # create the TreeViewColumns to display the data

        col = gtk.TreeViewColumn('Play')
        toggle = gtk.CellRendererToggle()
        toggle.set_property('activatable', True)
        toggle.connect('toggled', self._toggle_active, None)
        col.pack_start(toggle, True)
        col.set_attributes(toggle, active=0)
        self.treeview.append_column(col)

        col = gtk.TreeViewColumn('Title')
        cell = gtk.CellRendererText()
        col.pack_start(cell, True)
        col.set_attributes(cell, text=1)
        self.treeview.append_column(col)
        # Allow sorting on the column
        col.set_sort_column_id(1)

        col = gtk.TreeViewColumn('Album')
        cell = gtk.CellRendererText()
        col.pack_start(cell, True)
        col.set_attributes(cell, text=2)
        self.treeview.append_column(col)

        col = gtk.TreeViewColumn('Artist')
        cell = gtk.CellRendererText()
        col.pack_start(cell, True)
        col.set_attributes(cell, text=3)
        self.treeview.append_column(col)

        # make treeview searchable
        self.treeview.set_search_column(1)

        # Allow drag and drop reordering of rows
        self.treeview.set_reorderable(True)

        # create a new scrolled window.
        scrolled_window = gtk.ScrolledWindow()
        scrolled_window.set_border_width(0)
        scrolled_window.set_policy(gtk.POLICY_AUTOMATIC, gtk.POLICY_ALWAYS)
        scrolled_window.add(self.treeview)

        self.box.add(scrolled_window)
        self.window.show_all()


    def _toggle_active(self, cell, path, data=None):
        """
        Sets the toggled state on the toggle button to true or false.
        """
        self.liststore[path][0] = not self.liststore[path][0]

    
    def _update_list(self):
        self.liststore.clear()
        for item in self.search:
            e = [ True, item['title'], item['album'], item['artist'] ]
            self.liststore.append(e)
        

    @kaa.coroutine()
    def enter_callback(self, widget, data=None):
        self.search = yield kaa.beacon.query(keywords=data.get_text(), type='audio')
        self.search.signals['changed'].connect(self._update_list)
        self.search.monitor()
        self._update_list()


    def delete_event(self, widget, event, data=None):
        return False


    def destroy(self, widget, data=None):
        raise SystemExit
        

search = BeaconSearch()
kaa.main.run()
