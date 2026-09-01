#####################################################################
#Author : Evan
#####################################################################
#Date: 20201118
#content : modify BLE disconnect 5 times -> Modbus remove slave    
#####################################################################
#Date: 20221206
#content :
# 1.fix bug: BLE connect query data fail condition,delete delegate thread
# 2. new BLE connect status monitor record
#####################################################################
# Date : 20230112
# Content :
# 1. add modbus communication log
# 2. store logs 7 days
####################################################################


from bluepy.btle import Scanner, DefaultDelegate, Peripheral
import threading
import time
from configparser import ConfigParser
import logging
from logging.handlers import TimedRotatingFileHandler
# ~ logging.getLogger('werkzeug').disabled=True
import datetime
import gc
import ctypes
import inspect
import csv
from interface import Toplayer
import modbus_tk.modbus as modbus
from modbus_tk import hooks
import modbus_tk.defines as cst
import modbus_tk.modbus_tcp as modbus_tcp
from modbus_tk.utils import get_log_buffer
import paho.mqtt.client as mqtt
from interface import Toplayer
import json
from flask import Flask
from interface import Toplayer

log_filename = datetime.datetime.now().strftime("./log/%Y-%m-%d_%H_%M.log")

logging.basicConfig(level=logging.DEBUG,
                    format='%(asctime)s %(name)-12s %(levelname)-8s %(message)s',
                    handlers = [TimedRotatingFileHandler(filename =log_filename ,when="D",interval=1,backupCount=7)]
                    )

console = logging.StreamHandler()
console.setLevel(logging.INFO)
formatter = logging.Formatter('%(name)-12s: %(levelname)-8s %(message)s')
console.setFormatter(formatter)
logging.getLogger('').addHandler(console)

online_device=[]
connection_threads = []
fileConfig = "./conf/config.ini"

# logging disconnect
isRecord = 0
record_file = "./log/BLEconnect_%s.csv"%datetime.datetime.now().strftime("%Y-%m-%d_%H_%M")
csv_header=[]

def record_BLEconnect(header,data):
    with open(record_file,'a+') as csvfile:
        writer = csv.DictWriter(csvfile,fieldnames=csv_header)
        writer.writerow({header:data})
       


class Data(object):
    def __init__(self,):
        self._data = []
        self._id = 0
        self._name = ""

"""        
#####################
# Manager BT device #      
#####################
"""      

class Threadmanager(object):
    def __init__(self,mdl):
    # connection_threads : thread online list
    # online_device : mac online list
        global connection_threads
        global online_device
        global isRecord
        self.mdl = mdl
    # Define ble parameter (ID,NAME,MAC)
    # create thread to listen data from every bluetooth
    #@classmethod
    def createTd(self,devices,):
        try:
            for d in devices:
                device = d.split(';')
                id = int(device[0])
                threadname = device[1]
                mac = device[2]
                if(threadname not in csv_header):
                    csv_header.append(threadname)
                # ~ globals()['sensor%s'%id] = SENSOR_PARAM(id,threadname,mac)
                t = ConnectionHandlerThread(self.mdl,device)
                logging.info("[SETUP][ADD] SENSOR ID:%s Name:%s MAC:%s"%(id,threadname,mac))
                online_device.append(d)
                connection_threads.append(t)
                t.start()
                time.sleep(1)
            if(isRecord):
                with open(record_file,'a+',newline='') as csvfile:
                    writer = csv.DictWriter(csvfile,fieldnames=csv_header)
                    writer.writeheader()
        except:
            logging.error("[SETUP][FAIL] New Sensor Thread Function Error")
            pass
           
    def delTd(self,devices,):
        try:
            for d in devices:
                device = d.split(';')
                logging.info("[SETUP][Del] SENSOR ID:%s Name:%s MAC:%s"%(device[0],device[1],device[2]))
                id = device[0]

                for t in connection_threads:
                    if str(t._id) == id:
                        stop_thread(t)
                        try:
                            self.mdl.del_client(t._id)
                        except:
                            pass
                        connection_threads.remove(t)
                        online_device.remove(d)
                        gc.collect()
        except:
            logging.error("[SETUP][FAIL] Del Sensor Thread Error")
            pass
                   
     
       
class NotificationDelegate(DefaultDelegate):
    def __init__(self, sid,name,mdl):
        DefaultDelegate.__init__(self)
        self._id = sid  
        self._name = name
        self._mdl = mdl
        globals()['datam%s'%self._id]  = Data()
           
    def handleNotification(self, cHandle, data):
        raw_data = str(data,encoding="utf-8")
        strlist = raw_data.split(',')
        self._mdl.send(str(self._id),self._name,strlist)
"""        
##############################
# BlueTooth connect function #      
##############################
"""        
           
class ConnectionHandlerThread (threading.Thread):
    def __init__(self,mdl,device):
        threading.Thread.__init__(self)
        self._id = int(device[0])
        self._name = device[1]
        self._mac = device[2]
        global isRecord
        self.ifdo = True
        self.inf = device
        self._concnt = 0
        self.mdl = mdl
    def run(self):
        try:
            # ~ logging.info("[BLE][CONNECT] SENSOR ID:%s ,Name:%s ,MAC:%s"%(self._id ,self._name,self._mac))
            self.p = Peripheral(self._mac)
            # setup accept byte count
            self.p.setMTU(247)
            try:
                self.mdl.build_client(self._id)      
            except:
                pass
            self.p.setDelegate(NotificationDelegate(self._id,self._name,self.mdl))    
            logging.info("[BLE][CONNECT] SENSOR ID:%s ,Name:%s ,MAC:%s"%(self._id ,self._name,self._mac))
            discount = 0
            time.sleep(1)          
            while self.ifdo:
                if self.p.waitForNotifications(0.05):
                    discount = 0
                    continue
                else:
                    discount = discount+1
                    if (discount>500):
                        logging.warning("[DATA][FAIL] Querry Data (SNESOR ID:%s ,Name:%s ,Mac:%s "%(self._id ,self._name,self._mac))
                        discount = 0
                        # close call back thread
                        self.p.setDelegate(None)
                        self.p._stopHelper()
                        logging.warning("[BLE][REMOVE] TASK Done (SNESOR ID:%s ,Name:%s ,Mac:%s "%(self._id ,self._name,self._mac))
                        raise Exception        
         
        except Exception:
            logging.warning("[BLE][DISCONNECT] SENSOR ID:%s ,Name:%s ,Mac:%s "%(self._id ,self._name,self._mac))
            # compute reconnect count
            if(isRecord):
                record_BLEconnect(self._name,datetime.datetime.now().strftime("%Y-%m-%d_%H:%M:%S"))
            time.sleep(3)  
            self.reconnect()    
               
    def reconnect(self,):
        ###
        #print(connection_threads)
        ###
        #logging.info("[Ready] Check Sensor connect condition")
        try:
            self.ifdo = False
            rect = ConnectionHandlerThread(self.mdl,self.inf)
            rect.start()
           
            if rect.is_alive():
                #logging.info("[BLE][RECONNECT] SENSOR ID:%s ,Name:%s ,MAC:%s" %(self._id,self._name,self._mac))
                connection_threads.remove(self)
                connection_threads.append(rect)
                gc.collect()            
        except:
            logging.error("[BLE][FAIL] ReConnect Function Error")
            pass



class configsetup(object):
    def __init__(self):
        self.cfg = ConfigParser()
       
    def load(self,sections):
        conf_temp = []
        self.cfg.read(fileConfig)
        for key in self.cfg[sections]:
            conf_temp.append(self.cfg[sections][key])
        logging.info('[CONFIG][SUCCESSFUL] Load Configure')  
        return conf_temp
    def save(self,):
        with open(fileConfig,'w') as fo :
            self.cfg.write(fo)
            fo.close()
                                 
def _async_raise(tid, exctype):
    """raises the exception, performs cleanup if needed"""
    tid = ctypes.c_long(tid)
    if not inspect.isclass(exctype):
        exctype = type(exctype)
    res = ctypes.pythonapi.PyThreadState_SetAsyncExc(tid, ctypes.py_object(exctype))
    if res == 0:
        raise ValueError("invalid thread id")
    elif res != 1:
        # """if it returns a number greater than one, you're in trouble,
        # and you should call it again with exc=NULL to revert the effect"""
        ctypes.pythonapi.PyThreadState_SetAsyncExc(tid, None)
        raise SystemError("PyThreadState_SetAsyncExc failed")

def stop_thread(thread):
    _async_raise(thread.ident, SystemExit)

"""        
##################################
# Listen device parameter update #      
##################################
"""
   
def checkconfig(mdl):
    global online_device
    global connection_threads
    global isRecord

    # if modify ,compare mac with online and setup
    # if difference , define new parameter and new thread  
    # ~ logging.info("Check configure variation ready")
    #ConfigParser()
    Tdmgr = Threadmanager(mdl)
    while True:
        try:
            Con= configsetup()
            Con.cfg.read(fileConfig)
            if Con.cfg['Modify_flag']['mflag']=="change":
                logging.debug("[CONFIG][SETUP] config variation")
                temp=[]
                for key in Con.cfg['device']:
                    temp.append(Con.cfg['device'][key])
                online = set(online_device)
                setup = set(temp)
               
                del_target = list(online.difference(setup))
                add_target = list(setup.difference(online))
               
                Tdmgr.delTd(del_target)
                Tdmgr.createTd(add_target)
                Con.cfg.set('Modify_flag','mflag',"default")
                Con.save()
                             
            with open('./conf/backup.ini','w') as f:
                Con.cfg.write(f)  
           
        except :
            logging.warning("[CONFIG][FAIL] Reload Configure Setup Error")  
            Con= configsetup()
            Con.cfg.read('./conf/backup.ini')
            Con.cfg.set('Modify_flag','mflag',"change")
            with open('./conf/config.ini','w') as f:
                Con.cfg.write(f)
        time.sleep(10)
       
"""        
#######################
# Top Layer Protocol  #
# Modbus/Mqtt/Restful #      
#######################
"""
app = Flask(__name__)  
@app.route('/<string:name>/ID:<int:sid>/addr:<int:addr>', methods=['GET'])
def data(name,sid,addr):
    try:
        if addr>0 and addr<=len(globals()['datam%s'%sid]._data) and name == globals()['datam%s'%sid]._name:
            d  = str(globals()['datam%s'%sid]._data[addr-1])
            print(d)
            return d
        else:
            return "Exceed range or url error"
    except:
        pass
       
@app.route('/<string:name>/ID:<int:sid>', methods=['GET'])
def fulldata(name,sid):
    try:
        if name == globals()['datam%s'%sid]._name:
            dataDir= {}
            dataDir['feature'] = str(globals()['datam%s'%sid]._data)
            dataJson = json.dumps(dataDir)
            print(dataJson)
            return dataJson
        else:
            return "Exceed range or url error"
    except:
        pass

   
class Restful(Toplayer):
    def __init__(self,ip):
        self._ip = ip
        self.flag = True
    def server(self,):
        try:
            app.run(self._ip,port= 8088)
            logging.info('[Restful][CONNECT] Restful connect sucessful')
        except:
            logging.warning("[Restful][FAIL] Restful connect fail ")
    def build_client(self,sid):
        if self.flag ==True:
            self.t  = threading.Thread(target=self.server)
            self.t.start()
           
            self.flag = False
    def del_client(self,sid):
        try:
            del globals()['datam%s'%sid]
        except:
            pass
   
    def send(self,sid,name,datalist):
        # ~ pass
        try:
            globals()['datam%s'%sid]._id = sid
            globals()['datam%s'%sid]._name = name
            globals()['datam%s'%sid]._data = datalist
        except:
            logging.warning("[Restful][FAIL] Restful update data error ")
       



class Mqtt(Toplayer):
    def __init__(self,ip):
       
        client_id = "BT"
        self.client = mqtt.Client(client_id = client_id)
        user = ""
        password = ""
        self._ip = ip
       
    def build_client(self,sid):
        try:
            self.client.connect(self._ip,18831,100)
            logging.info('[Mqtt][CONNECT] Mqtt connect sucessful')
        except:
            logging.warning("[Mqtt][FAIL] Mqtt connect fail ")
    def del_client(self,sid):
        pass
        # ~ self.client.disconnect()
        # ~ print("disconnect")
       
    def send(self,sid,name,datalist):
       
        dataDir= {}
        dataDir['feature'] = str(datalist)
        dataJson = json.dumps(dataDir)
        print(dataJson)
        self.client.publish("/%s/ID:%s"%(name,sid),dataJson)  
       
       


class Modbus(Toplayer):
    def __init__(self,ip):
        try:

            # parameter(ip/port)
            global isRecord
            self._ip = str(ip)
            #logging.info("Modbus IP:%s "%self._ip)              
            self.server = modbus_tcp.TcpServer(address = self._ip,port=502)
            #self.server = modbus_tcp.TcpServer()
            self.server.start()
           
            if (isRecord):
                hooks.install_hook("modbus.Server.before_handle_request",self.on_receive)
                hooks.install_hook("modbus.Server.after_handle_request",self.on_response)

            logging.info('[MODBUS][START] Modbus Server Start')
           
        except ValueError as ex:
            logging.warning(ex)
            print('Server create fail')
            self.server.stop()
            self.server._do_exit()
   
    def build_client(self,sid):

        globals()['slave%s'%sid] = self.server.add_slave(int(sid))
        globals()['slave%s'%sid].add_block(str(sid), cst.HOLDING_REGISTERS, 0,50)
       
        logging.info("[MODBUS][ADD] Modbus Add Slave %s"%sid)  
         
    def del_client(self,sid):
        self.server.remove_slave(int(sid))
        logging.info("[MODBUS][Del] Modbus Delete Slave %s"%sid)
       
    def send(self,sid,name,datalist):
        # ~ pass
        try:
            for addr in range(len(datalist)):
                data = int(float(datalist[addr]))
                if data>=65535:
                    data = 65535
                if data<0:
                    data = 0
                globals()['slave%s'%sid].set_values(str(sid), addr, data)
                #print("ID:%s , add:%s , data:%s"%(sid,addr,data))
        except:
            logging.warning("[MODBUS][FAIL] Slave:%s Send Data Error"%self._id)
           
    def on_receive(self,msgs):
        logging.debug("[Slave ID:%s] %s"%(get_log_buffer("",msgs[1][6:7]),get_log_buffer("-->",msgs[1][6:])))
        print("[Slave ID:%s] %s"%(get_log_buffer("",msgs[1][6:7]),get_log_buffer("-->",msgs[1][6:])))
    def on_response(self,msgs):
        logging.debug("[Slave ID:%s] %s"%(get_log_buffer("",msgs[1][6:7]),get_log_buffer("<--",msgs[1][6:])))
        print("[Slave ID:%s] %s"%(get_log_buffer("",msgs[1][6:7]),get_log_buffer("<--",msgs[1][6:])))
       
if __name__ == "__main__":  
    # load configure and return setup ble mac

    cfg = configsetup()
    device_list = cfg.load('device')
    ip = cfg.cfg['Toplayer']['hostip']
    protocol = cfg.cfg['Toplayer']['Protocol']
    isRecord =  int(cfg.cfg['Modify_flag']['record'])
    module = locals()[protocol](ip)
    Tdmgr = Threadmanager(module)
    Tdmgr.createTd(device_list)
    # To check Configure update
    th = threading.Thread(target=checkconfig,args=(module,))#,daemon=True)
    th.start()