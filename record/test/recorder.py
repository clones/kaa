from kaa.record.dvb import DvbDevice

dvb = DvbDevice('/dev/dvb/adapter0', '/home/dmeyer/.freevo/channels.conf', 9)
print dvb.get_card_type()
