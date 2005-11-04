import os

class Item(object):
    def __init__(self, data, parent, db):
        self.data = data
        self.db = db
        self.parent = None

        # self.dirname always ends with a slash
        # if the item is a dir, self.filename also ends with a slash
        # self.url does not end with a slash (except root)
        
        # If parent is not set, this is a root node.
        # A root node is always part of the db already
        if not parent:
            self.url = 'file:/' + self.data['name']
            self.dirname = self.data['name']
            self.filename = self.data['name']
            self.isdir = True
            self.basename = '/'
            self.dbid = self.data['type'], self.data["id"]
            return

        if isinstance(self.data, dict):
            self.basename = self.data['name']
            self.dbid = self.data['type'], self.data["id"]
        else:
            self.basename = self.data
            self.dbid = None
            
        # check if the item is based on a file
        if not isinstance(parent, str):
            self.parent = parent
            parent = parent.filename
        if parent:
            self.url = 'file:/' + parent + self.basename
            self.dirname = parent
            self.filename = parent + self.basename
            if os.path.isdir(self.filename):
                self.filename += '/'
                self.isdir = True
            else:
                self.isdir = False
                    
        # TODO: handle files/parents not based on file:


    def __str__(self):
        if isinstance(self.data, str):
            return 'new file %s' % self.data
        return self.data['name']


    def __getitem__(self, key):
        if self.data.has_key(key):
            return self.data[key]
        if self.data.has_key('tmp:' + key):
            return self.data['tmp:' + key]

        # TODO: maybe get cover from parent (e.g. cover in a dir)
        # Or should that be stored in each item
        
        return None


    def __del__(self):
        print 'del %s' % self


