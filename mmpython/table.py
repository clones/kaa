
class Table:
    def __init__(self, hashmap, name):
        self.dict = hashmap
        self.name = name
        
    def __setitem__(self,key,value):
        self.dict[key] = value
        
    def __getitem__(self,key):
        if self.dict.has_key(key):
            return self.dict[key]
        else:
            return None
         
    def getstr(self,key):
        s = self[key]
        if s and len(s.__str__()) < 100: 
            return s
        else:
            return "Not Displayable"       
         
    def has_key(self, key):
        return self.dict.has_key(key)    
    
    def __str__(self):
        header = "\nTable %s:" % self.name 
        result = reduce( lambda a,b: self[b] and "%s\n        %s: %s" % \
                         (a, b.__str__(), self.getstr(b)) or a, self.dict.keys(), header )
        return result

    def accept(self,mi):
        pass