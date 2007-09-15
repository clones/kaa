import sys
import kaa.notifier
import kaa.beacon
import kaa.netsearch.feed

if len(sys.argv) > 1:
    if sys.argv[1] in ('--update', '-u'):
        if not kaa.netsearch.feed.list_channels():
            print 'no channels defined'
            sys.exit(0)
        kaa.beacon.connect()
        kaa.netsearch.feed.update(verbose=True).connect(sys.exit)
        kaa.notifier.loop()
        sys.exit(0)


kaa.beacon.connect()
kaa.netsearch.feed.add_channel('http://foo', 'bar')

sys.exit(0)

# import gtk for gui
import pygtk
pygtk.require('2.0')
import gtk
import gtk.glade

kaa.notifier.init('gtk')
# kaa.beacon.connect()

GLADEFILE = 'test/feedmanager.glade'

class Manager(object):
    def __init__(self):
        self.xml = gtk.glade.XML(GLADEFILE, 'manager')
        self.xml.signal_autoconnect (self)

        self.treestore = gtk.TreeStore(str)
        self.tree = self.xml.get_widget("list")
        self.tree.set_model(self.treestore)
        column = gtk.TreeViewColumn("URL", gtk.CellRendererText(), text=0)
        self.tree.append_column(column)
        self._rebuild()

    def _rebuild(self):
        self.channels = []
        self.treestore.clear()
        for channel in kaa.netsearch.feed.list_channels():
            self.treestore.append(None, [ channel.url ])
            self.channels.append(channel)

    def _get_selection(self):
        sel = self.tree.get_selection().get_selected_rows()[1]
        if not sel:
            return None
        return self.channels[sel[0][0]]

    def on_add_clicked(self, args):
        Edit(callback=self._rebuild)
        
    def on_configure_clicked(self, args):
        if self._get_selection():
            Edit(self._get_selection(), self._rebuild)
    
    def on_remove_clicked(self, args):
        if self._get_selection():
            kaa.netsearch.feed.remove_channel(self._get_selection())
            self._rebuild
            
    def quit(self, *args):
        sys.exit(0)


class Edit(object):
    def __init__(self, channel=None, callback=None):
        self.xml = gtk.glade.XML(GLADEFILE, 'edit')
        self.xml.signal_autoconnect (self)
        self.win = self.xml.get_widget("edit")
        self.channel = channel
        if channel:
            for widget in ('url', 'dirname'):
                self.get_widget(widget).set_text(getattr(channel, widget))
                self.xml.get_widget(widget).set_sensitive(False)
        self.win.show()
        self.callback = callback
        

    def get_widget(self, name):
        return self.xml.get_widget(name)
    

    def on_all_items_toggled(self, button):
        self.xml.get_widget("num").set_sensitive(not button.get_active())
        self.xml.get_widget("num_label").set_sensitive(not button.get_active())
        

    def on_download_toggled(self, button):
        self.xml.get_widget("keep").set_sensitive(button.get_active())


    def on_cancel_clicked(self, args):
        self.win.destroy()
        if self.callback:
            self.callback()

    def on_ok_clicked(self, args):
        # get data
        url = self.get_widget("url").get_text()
        destdir = self.get_widget("dirname").get_text()
        download = self.xml.get_widget("download").get_active()
        keep = self.xml.get_widget("keep").get_active()
        num = 0
        if not self.xml.get_widget("all_items").get_active():
            num = int(self.xml.get_widget("num").get_value())

        if self.channel:
            self.channel.configure(download, num, keep)
            self.win.destroy()
            if self.callback:
                self.callback()
            return

        if url and destdir:
            kaa.netsearch.feed.add_channel(url, destdir, download, num, keep)
            self.win.destroy()
            if self.callback:
                self.callback()
            return
        
        # no idea how this works with glade.
        # FIXME: make the dialog modal
        dialog = gtk.MessageDialog(
            parent = self.win, flags = gtk.DIALOG_DESTROY_WITH_PARENT,
            type = gtk.MESSAGE_INFO, buttons = gtk.BUTTONS_OK,
            message_format = 'You need to fill in an URL and a directory where\n' + \
            'the items should be stored.')
        dialog.set_title('Error')
        dialog.connect('response', lambda dialog, response: dialog.destroy())
        dialog.show()
        return
    
m = Manager()
kaa.notifier.loop()
