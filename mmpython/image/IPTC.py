from struct import unpack

# todo: Intend correctly

class IPTC:
    def __init__(self,hash):
        self.hash = hash
    
    def __getitem__(self,key):
        if self.hash and self.hash.has_key(key):
            item = self.hash[key]
            if len(item) == 0: return None
            elif len(item) == 1: return item[0]
            else: return tuple(item)
        else:
            return None
       
    def keys(self):
        if self.hash:
            return self.hash.keys()
        else:
            return []

def flatten(list):
    for i in list.keys():
        val = list[i]
        if len(val) == 0: list[i] = None
        elif len(val) == 1: list[i] = val[0]
        else: list[i] = tuple(val)
    return list

def parseiptc(app):
    iptc = {}
    print app[:14]
    if app[:14] == "Photoshop 3.0\x00":
       app = app[14:]
    if 1:
       # parse the image resource block
       offset = 0
       while app[offset:offset+4] == "8BIM":
          offset = offset + 4
          # resource code
          code = unpack("<H", app[offset:offset+2])[0]
          offset = offset + 2
          # resource name (usually empty)
          name_len = ord(app[offset])
          name = app[offset+1:offset+1+name_len]
          offset = 1 + offset + name_len
          if offset & 1:
              offset = offset + 1
          # resource data block
          size = unpack("<L", app[offset:offset+4])[0]
          offset = offset + 4
          if code == 0x0404:
              print "iptc found."
              # 0x0404 contains IPTC/NAA data
              data = app[offset:offset+size]
              break
          offset = offset + size
          if offset & 1:
              offset = offset + 1
       if not data:
          None
       offset = 0
       iptc = {}
       while 1:
           intro = ord(data[offset])
           if intro != 0x1c:
               return iptc
           key = unpack('>H',data[offset+1:offset+3])[0]
           len = unpack('>H',data[offset+3:offset+5])[0]
           val = data[offset+5:offset+len+5]
           #print "0x%x (%d) %s" % (key, len, val)
           if iptc.has_key(key):
               iptc[key].append(val)
           else:
               iptc[key] = [val]
           offset += len + 5
    return iptc
    
def getiptcinfo(file):
   app = file.read(4)
   if app[:4] == 'MM\x00\x2a':
      (offset,) = unpack(">I", file.read(4))
      file.seek(offset)
      (len,) = unpack(">H", file.read(2))
      print "tiff motorola, len=%d" % len
      app = file.read(len*12)
      for i in range(len):
          (tag, type, length, value, offset) = unpack('>HHIHH', app[i*12:i*12+12])
          print "tag: 0x%.4x, type 0x%.4x, len %d, value %d, offset %d)" % (tag,type,len,value,offset)
          if tag == 0x8649:
              file.seek(offset)
              return flatten(parseiptc(file.read(1000)))
      return None
   elif app[:4] == 'II\x2a\x00':
      (offset,) = unpack("<I", file.read(4))
      file.seek(offset)
      (len,) = unpack("<H", file.read(2))
      print "tiff intel, len=%d" % len
      app = file.read(len*12)
      for i in range(len):
          (tag, type, length, offset, value) = unpack('<HHIHH', app[i*12:i*12+12])
          print "tag: 0x%.4x, type 0x%.4x, len %d, value %d, offset %d)" % (tag,type,len,value,offset)
          if tag == 0x8649:
              file.seek(offset)
              return flatten(parseiptc(file.read(1000)))
      return IPTC(None)
   elif app[:2] == '\xff\xd8':
      app = app[2:] + file.read(2)
      while 1:
          segtype = app[:2]
          (seglen,) = unpack(">H", app[2:])
          print "%x, len=%d" % (ord(segtype[1]),seglen)          
          if segtype == '\0xFF\0xD9':
              return None
          elif segtype != '\xff\xed':
              file.seek(seglen-2,1)
              app = file.read(4)
          else:
              app = file.read(seglen)
              return flatten(parseiptc(app))
      return None
   else: return None
    


if __name__ == '__main__':
    import sys
    o = getiptcinfo(open(sys.argv[1], 'rb'))
    print "IPTC: "
    for k in o.keys():
        print "%d -> %s" % (k,o[k])
    