def BeaconServer(database):
    import server
    return server.Server(database)

def HardwareMonitorServer():
    import hwmon.server
    return hwmon.server.Server()
        
def HardwareMonitorClient():
    import hwmon
    return hwmon
        
def Thumbnailer():
    import thumbnailer
    return thumbnailer.init()

def connect_hardware_monitor():
    import hwmon.server
