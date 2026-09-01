from configparser import ConfigParser
from server import wbserver
from bluepy.btle import Scanner
import os
import time
from Timeout import timeout
from xmodem import XMODEM
import threading 
import serial
import queue


fileConfig = "./conf/config.ini"

class configsetup():
    def __init__(self):
        self.cfg = ConfigParser()
        
    def load(self,sections):
        conf_temp = []
        self.cfg.read(fileConfig)
        for key in self.cfg[sections]:
            conf_temp.append(self.cfg[sections][key])  
        return conf_temp 
    def save(self,):
        with open(fileConfig,'w') as fo :
            self.cfg.write(fo)
            fo.close() 

c  = configsetup()




class Parameter():
    def __init__(self):
        self.check = False
t = Parameter()

class IAP(threading.Thread):
    def __init__(self,inf):
        threading.Thread.__init__(self)
        self.conflag = True
        self.inf = inf
        self._file = inf[3]
        self.upflg = False
 
    def connect(self):
        try:
            port = "/dev/ttyUSB0"
            self.ser =serial.Serial(port,baudrate = 115200)
            self.ser.timeout=10
            if self.ser.isOpen():
                print("open success")
            else:
                print("fail") 
        except:
            print("serial port not exist")
    def getc(self,size, timeout=0.01):
        return self.ser.read(size) or None
    def putc(self,data, timeout=0.01):
        return self.ser.write(data)  # note that this ignores the timeout
        
    def run(self):

        self.connect()
        con = True
        cnt = 0
        try:
            while self.conflag:
                mactf = self.inf[2].replace(":","")
                self.ser.write(b'AT+DCON=1\r\n')
                time.sleep(0.5)
                self.ser.write(('AT+CON='+str(mactf)+'\r\n').encode())
                t.check = True
                print("try to connect")
                receive = self.ser.readline().decode()
                print(receive)
                t.check = False
                
                
                if '+Connect Failed' in receive or '+CON Error' in receive or len(receive)==0:                           
                    cnt+=1
                    if cnt >2:
                        self.upflg = False
                        rst = False
                        print({"INFO":"[WARNING] BLE CONNECT FAIL"})
                        break
                if '+MTU:244' in receive:
                    print({"INFO":"[INFO] BLE CONNECT SUCCESSFUL"})
                    cnt=0
                    self.conflag = False
                    rst=True
                    time.sleep(0.1)
        
                    while rst:
                        self.ser.write(b'request\r\n')
                        t.check = True
                        receive = self.ser.readline().decode()
                        print(receive) 
                        t.check = False
                        if 'RESTART' in receive :
                            time.sleep(0.5)
                            self.ser.write(b'request')
            
                            rst = False
                            iap = True
                            while iap:
                                t.check = True
                                receive = self.ser.readline().decode()
                                print(receive) 
                                t.check = "bbk"
                                if "IAP processing" in receive:
                                    try:
                                        iap=False
                                        print({"INFO":"[INFO] UPDATING (ID:%s,NAME:%s,MAC:%s) "%(self.inf[0],self.inf[1],self.inf[2])})
                                        modem = XMODEM(self.getc, self.putc,size = 128,mode='ymodem')
                                        aa = modem.send(self._file)
                                        self.ser.write(b'AT+DCON=1\r\n')
                                        self.upflg = True
                                        print({"FLASHED_OK":str(self.inf[0]),"INFO": "[INFO] UPDATE FINISH (ID:%s,NAME:%s,MAC:%s) "%(self.inf[0],self.inf[1],self.inf[2])})
                                        break  
                                    except:
                                        print({"INFO":"[INFO] UPDATE FAIL"})
                                        self.ser.write(b'AT+DCON=1\r\n')
                                        break
                                        
        except KeyboardInterrupt:
            if serial != None:
                serial.close()
                




def run(inf):
    

    while True:
        # ~ try:
        _id = inf['ID']
        name = inf['NAME']
        mac = inf['MAC']
        filepath = inf['FILEPATH']
        dev = [_id,name,mac,filepath]
        
        c.cfg.read(fileConfig)
        del c.cfg["device"]["s%s"%_id]        
        c.cfg.set('Modify_flag','mflag',"change")
        c.save()
        time.sleep(5)
        
        ota = IAP(dev)
        to = threading.Thread(target=timeout,args=(ota,t))
        to.start()
        ota.start()
        ota.join()

        c.cfg.set('device','s%s'%_id,_id+";"+name+";"+mac)
        c.cfg.set('Modify_flag','mflag',"change")
        c.save()
            
            
        # ~ except:
            # ~ print("fire fail")
        time.sleep(5)


                    
if __name__ == "__main__":
    run({"ID":"1","NAME":"Fire","MAC":"e0:7d:ea:eb:15:68","FILEPATH":"/home/pi/ework/Bluetooth/Bin/STM32F7_1113.bin"})
