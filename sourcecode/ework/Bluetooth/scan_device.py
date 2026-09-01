
from bluepy.btle import Scanner, DefaultDelegate, Peripheral
from configparser import ConfigParser

def Scan_device():
    scanner = Scanner(0)
    flag = 0
    devices = scanner.scan(5.0)
    print("[INFO] Device Name :\n")
    #scan device
    for dev in devices:
        for (adtype, desc, value) in dev.getScanData():
            if desc =="Complete Local Name":
                flag = flag +1
                print("%s)%s (mac:%s)"%(flag,value,dev.addr))
                
def read():
    a = []
    cfg = ConfigParser()
    cfg.read('./conf/config.ini')
    for key in cfg['mac_address']:
        a.append(key)
    for i in a:
        print(i)

        

Scan_device()
