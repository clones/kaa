
class Table:
    def __init__(self, hashmap):
        self.dict = hashmap
        
    def __setitem__(self,key,value):
        self.dict[key] = value
        
    def __getitem__(self,key):
        if self.dict.has_key(key):
            return self.dict[key]
        else:
            return None
            
    def accept(self,mi):
        pass