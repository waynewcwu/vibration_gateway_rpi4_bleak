#--------------------------------------------------------------------
# Date : 2021/08/23
# version : UI backend v3 (for REYAX chip)
# 1. add wifi function
# 2. Modify mcu remote deploy UI 
# 3. Modify GPIO RESET function
#--------------------------------------------------------------------
# Date : 2022/10/14
# 1. Modify wifi setup : add scan_ssid for auto connect hidden wifi
#--------------------------------------------------------------------

from flask import Flask,request
from flask_cors import CORS
import json
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
import RPi.GPIO as GPIO

GPIO_reset_in = 20
GPIO_LED_out = 21
GPIO.setmode(GPIO.BCM)
GPIO.setup(GPIO_reset_in,GPIO.IN,pull_up_down=GPIO.PUD_UP)
GPIO.setup(GPIO_LED_out,GPIO.OUT,initial = False)


lock = threading.Lock()
q = queue.Queue()
fileConfig = "./conf/config.ini"
wb = wbserver(8085)
wb.start()

def wss(information):
    wb.server.send_message_to_all(information)


class Parameter():
    def __init__(self):
        self.check = False
t = Parameter()

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
app = Flask(__name__)  
CORS(app)

@app.route('/bluetooth/device/add', methods=['POST'])
def add_dev():

    data = request.stream.read(int(request.headers['Content-Length']))
    data = json.loads(data)
    fblog = []
    for inf in data:
        id = inf['ID']
        name = inf['NAME']
        mac = inf['MAC']
        flag = True
        c.cfg.read(fileConfig)
        for key in c.cfg['device']:
            data = c.cfg['device'][key]
            data = data.split(";")
            if data[0]==id or data[2]==mac:
                flag = False
                fblog.append({"INFO":"[FAIL] Device already exist"})
                return json.dumps(fblog)

        if flag==True:
            c.cfg.set('device','s%s'%id,id+";"+name+";"+mac)
            c.cfg.set('Modify_flag','mflag',"change")
            c.save()
            fblog.append({"INFO":"[INFO] Device add successful (ID:%s,NAME:%s,MAC:%s) "%(id,name,mac)})

    return json.dumps(fblog)
    
@app.route('/bluetooth/device/remove', methods=['POST'])    
def remove_dev():
    data = request.stream.read(int(request.headers['Content-Length']))
    information = json.loads(data)
    c.cfg.read(fileConfig)
    fblog = []
    for key in c.cfg['device']:
        data = c.cfg['device'][key]
        data = data.split(";")

        for inf in information:
            id = inf['ID']
            name = inf['NAME']
            mac = inf['MAC']
            if data[0]==id and data[1]==name and data[2]==mac:
                del c.cfg["device"][key]
                c.save()
                fblog.append({"INFO":"[INFO] Device remove successful (ID:%s,NAME:%s,MAC:%s) "%(id,name,mac)})                
    c.cfg.set('Modify_flag','mflag',"change")
    c.save()
    return json.dumps(fblog)
   
@app.route('/bluetooth/device/read', methods=['POST'])   
def read():
    try:
        device_list = c.load('device')
        devices = []
        for d in device_list:
            device = d.split(';')
            id = str(device[0])
            name = device[1]
            mac = device[2]
            devices.append({"ID":id,"NAME":name,"MAC":mac})
        
        devjson = json.dumps(devices)

        return devjson
    except:
        return "Nothing"
       
@app.route('/bluetooth/device/scan', methods=['POST'])      
def scan():
    fblog=[]
    lock.acquire()
    scanner = Scanner(0)
    devices = scanner.scan(3.0)
    flag = 0
    fblog.append({"INFO":"[INFO] Device Name :\n"})
    print("[INFO] Device Name :\n")
    for dev in devices:
        for (adtype, desc, value) in dev.getScanData():
            if desc =="Complete Local Name":
                flag = flag +1
                fblog.append({"INFO":"{0}){1} (mac: {2}) {3} dB ".format(flag,value,dev.addr,dev.rssi)})

    fblog.append({"INFO":"[INFO] SCAN FINISH"})
    lock.release()
    return json.dumps(fblog)

@app.route('/get/protocol', methods=['POST'])     
def protocol():
    fblog = []
    data = request.stream.read(int(request.headers['Content-Length']))
    inf = json.loads(data)
    protocol = inf['PROTOCOL']
    c.cfg.read(fileConfig)
    c.cfg.set('Toplayer','protocol',str(protocol))
    c.save()
    fblog.append({"INFO":"[INFO] Protocol : %s "%protocol})
    fblog.append({"INFO":"[INFO] PLEASE RESTART Raspi"})
    return json.dumps(fblog)
  
@app.route('/bleota', methods=['POST'])      
def bleota():
    
    lock.acquire()
    data = request.stream.read(int(request.headers['Content-Length']))
    devinf = json.loads(data)  
    wss(json.dumps({"INFO":"[INFO] OTA Start "}))#(ID:%s,NAME:%s,MAC:%s) "%(_id,name,mac)}))
    print(devinf)
    for inf in devinf:
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
        to = threading.Thread(target=timeout,args=(ota,t,wb))
        to.start()
        ota.start()
        ota.join()

        c.cfg.set('device','s%s'%_id,_id+";"+name+";"+mac)
        c.cfg.set('Modify_flag','mflag',"change")
        c.save()
   
    wss(json.dumps({"INFO":"[INFO] OTA FINISH"}))
    
    # ~ m  = threading.Thread(target=mgr,args=(devinf,))
    # ~ m.start()
    # ~ m.join()
    
    lock.release()     
    

    return "OK"
###################################################################   
            
@app.route('/update/config/network', methods=['GET','POST'])             
def setupnetwork(inf=None):
    if inf ==None:
        data = request.stream.read(int(request.headers['Content-Length']))
        if len(data)!=0:
            inf = json.loads(data)
    path = "/etc/network/interfaces"
    dhcp_path = "/etc/dhcpcd.conf"
    wpa_path = "/etc/wpa_supplicant/wpa_supplicant.conf"
    nwtype = inf['NWTYPE']
    print(nwtype)
    ip = inf['IP'].strip()
    netmask = inf['NETMASK'].strip()
    gateway = inf['GATEWAY'].strip()
    if (str(nwtype)=="WIFI"):
        ssid = inf['SSID']
        pwd = inf['PWD']
        print(ssid)
        print(pwd)
        
        # wifi information
        f = open(path,'r')
        content = f.readlines()
        f.close()
        del content[8:]
        content.insert(8,"#auto wlan0\n")
        content.insert(9,"#iface lo inet loopback\n")
        content.insert(10,"#iface eth0 inet dhcp\n")
        content.insert(11,"#allow-hotplug wlan0\n")
        content.insert(12,"#iface wlan0 inet static \n")
        content.insert(13,"#address "+str(ip)+"\n")
        if (len(netmask)!=0):
            content.insert(14,"#netmask "+str(netmask)+"\n")
        else:
            content.insert(14,"\n")
        if (len(gateway)!=0):
            content.insert(15,"#gateway "+str(gateway)+"\n")
        else:
            content.insert(15,"\n")
        content.insert(16,"#wpa-conf /etc/wpa_supplicant/wpa_supplicant.conf\n")
        content.insert(17,"#iface default inet dhcp\n")
        f = open(path,'w')
        content = "".join(content)
        f.write(content)
        f.close()
        
        # wifi wpa setup
        f = open(wpa_path,'r')
        content = f.readlines()
        f.close()
        f = open(wpa_path,'w')
        del content[3:]
        content.insert(4,'network={ \n')
        content.insert(5,'ssid="'+str(ssid)+'"\n')
        if (len(pwd)!=0):
            content.insert(6,'psk="'+str(pwd)+'"\n')
            content.insert(7,'key_mgmt=WPA-PSK \n')
        else:
            content.insert(6,'\n')
            content.insert(7,'key_mgmt=NONE \n')
        content.insert(8,'scan_ssid=1 \n')
        content.insert(9,'}\n')
        content = "".join(content)
        f.write(content)
        f.close()
        
        # wifi dhcp setup
        
        # netmask change format
        netmasklist = netmask.split(".")
        number_sum = 0
        for n in netmasklist:
            netmask_number = format(int(n),"b")

            for i in netmask_number:
                number_sum+=int(i)
        print(number_sum)
        f = open(dhcp_path,'r')
        dhcp_inf = f.readlines()
        f.close()
        f = open(dhcp_path,'w')
        dhcp_inf.append('\n\n\n\n\n\n\n\n\n\n')
        if(len(dhcp_inf[64:])!=0):
            del dhcp_inf[64:]
        dhcp_inf.insert(64,'interface wlan0\n')
        dhcp_inf.insert(65,'static ip_address='+str(ip)+'/'+str(number_sum)+"\n")
        if (len(gateway)!=0):
            dhcp_inf.insert(66,"static routers="+str(gateway)+"\n")
        else:
            dhcp_inf.insert(66,"\n")
        dhcp_inf="".join(dhcp_inf)
        f.write(dhcp_inf)
        f.close()
                
        wss(json.dumps({"INFO":"[INFO] NETWORK SETTING FINISH"}))
        wss(json.dumps({"INFO":"[INFO] PLEASE RESTART"}))
        
        
    
    if (nwtype=="ETH"):
        

        
        f = open(path,'r')
        content = f.readlines()
        f.close()
        del content[8:]
        content.insert(8,"auto eth0\n")
        content.insert(9,"iface eth0 inet static\n")
        content.insert(10,"address "+str(ip)+"\n")
        content.insert(11,"netmask "+str(netmask)+"\n")
        if (len(gateway)!=0):
            content.insert(12,"gateway "+str(gateway)+"\n")
          

        f = open(path,'w')
        content = "".join(content)
        f.write(content)
        f.close()
        
                # remove wifi setup
        f = open(dhcp_path,'r')
        dhcp_inf = f.readlines()
        f.close()
        f = open(dhcp_path,'w')
        if(len(dhcp_inf)>=64):
            del dhcp_inf[64:]
        dhcp_inf="".join(dhcp_inf)
        f.write(dhcp_inf)
        f.close()
        
        wss(json.dumps({"INFO":"[INFO] NETWORK SETTING FINISH"}))
        wss(json.dumps({"INFO":"[INFO] PLEASE RESTART"}))
      
    return "OK"
    
    
@app.route('/get/config/network', methods=['POST'])             
def getnetwork(inf=None):
    
    f = open("/etc/network/interfaces",'r')
    content = f.readlines()
    f.close()
    nwtype = content[8].split(" ")[1]

    if ("eth0" in nwtype):

        ip = content[10].split(" ")[1]
        netmask = content[11].split(" ")[1]
        try:
            gateway = content[12].split(" ")[1]
        except:
            gateway = ""
        nwtype = "ETH"
        return json.dumps({"IP":ip,"NETMASK":netmask,"GATEWAY":gateway,"NWTYPE":nwtype})
        
    if("wlan0" in nwtype):
        f = open("/etc/wpa_supplicant/wpa_supplicant.conf",'r')
        wpacontent = f.readlines()
        f.close()
        ip = content[13].split(" ")[1]
        try:
            netmask = content[14].split(" ")[1]
        except:
            netmask = ""
        try:
            gateway = content[15].split(" ")[1]
        except:
            gateway=""
        nwtype = "WIFI"
         
        ssid = eval(wpacontent[4].split("=")[1])
        
        try:
            pwd = eval(wpacontent[5].split("=")[1])
        except:
            pwd = ""
        print(ssid)
        print(ip)
        return json.dumps({"IP":ip,"NETMASK":netmask,"GATEWAY":gateway,"NWTYPE":nwtype,"SSID":ssid,"PWD":pwd})
        
        
    
@app.route('/mcu/setting/reboot', methods=['POST'])       
def reboot():
    os.system("sudo reboot")
    return "OK"

@app.route('/to/default/reset', methods=['POST'])       
def reset():
    print('reset')
    setupnetwork(inf={"IP":"172.0.0.1","NETMASK":"255.255.255.0","GATEWAY":"172.0.0.254","NWTYPE":"ETH"})
    c.cfg.read(fileConfig)
    for key in c.cfg['device']:
        del c.cfg["device"][key]
    c.save()
    os.system("sudo reboot")
    return "OK"
    

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
            self.ser.timeout=3
            if self.ser.isOpen():
                print("open success")
            else:
                print("fail") 
        except:
            wss(json.dumps({"INFO":"[WARNING] No serial module"}))
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
                self.ser.write(b'AT+DCON=0\r\n')
                time.sleep(1)
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
                        wss(json.dumps({"INFO":"[WARNING] BLE CONNECT FAIL(ID:%s,NAME:%s,MAC:%s) "%(self.inf[0],self.inf[1],self.inf[2]),"FLASHED_NG":str(self.inf[0])}))
                        break
                if '+MTU' in receive:
                    wss(json.dumps({"INFO":"[INFO] BLE CONNECT SUCCESSFUL"}))
                    cnt=0
                    self.conflag = False
                    rst=True
                    time.sleep(0.1)
        
                    while rst:
                        print('request')
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
                                self.ser.timeout=60
                                time.sleep(0.5)
                                t.check = "bbk"
                                if "IAP processing" in receive:
                                    try:
                                        iap=False
                                        wss(json.dumps({"UPDATE":"on","INFO":"[INFO] UPDATING (ID:%s,NAME:%s,MAC:%s) "%(self.inf[0],self.inf[1],self.inf[2])}))
                                        modem = XMODEM(self.getc, self.putc,size = 128,mode='ymodem')
                                        aa = modem.send(self._file)
                                        self.upflg = True
                                        self.ser.write(b'AT+DCON=0\r\n')
                                        if aa :
                                            wss(json.dumps({"FLASHED_OK":str(self.inf[0]),"INFO": "[INFO] UPDATE FINISH (ID:%s,NAME:%s,MAC:%s) "%(self.inf[0],self.inf[1],self.inf[2])}))
                                        else:
                                            wss(json.dumps({"UPDATE":"off","INFO":"[INFO] UPDATE FAIL(ID:%s,NAME:%s,MAC:%s) "%(self.inf[0],self.inf[1],self.inf[2]),"FLASHED_NG":str(self.inf[0])}))
                                        break    
                                    except:
                                        wss(json.dumps({"INFO":"[INFO] UPDATE FAIL(ID:%s,NAME:%s,MAC:%s) "%(self.inf[0],self.inf[1],self.inf[2]),"FLASHED_NG":str(self.inf[0])}))
                                        self.ser.write(b'AT+DCON=0\r\n')
                                        break
                                        
        except :
            wss(json.dumps({"INFO":"[INFO] UPDATE FAIL(ID:%s,NAME:%s,MAC:%s) "%(self.inf[0],self.inf[1],self.inf[2]),"FLASHED_NG":str(self.inf[0])}))
            if self.ser != None:
                self.ser.close()


def gpio_callback(GPIO_reset_in):
    cnt=1
    if not GPIO.input(GPIO_reset_in):
        for i in range(3):
            if not GPIO.input(GPIO_reset_in):
                cnt = cnt+1
                if cnt>3:
                    cnt = 0
                    GPIO.output(GPIO_LED_out,True)
                    time.sleep(3)
                    GPIO.output(GPIO_LED_out,False)
                    reset()
            time.sleep(1)
        print("end")

if __name__ == "__main__":
    GPIO.add_event_detect(GPIO_reset_in,GPIO.RISING,callback=gpio_callback)
    app.run("0.0.0.0",port=8082)
 
