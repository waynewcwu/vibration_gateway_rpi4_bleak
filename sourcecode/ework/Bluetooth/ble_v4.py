
from bluepy.btle import Scanner, DefaultDelegate, Peripheral
import threading
import time
import queue
import modbus_tk.modbus as modbus
import modbus_tk.defines as cst
import modbus_tk.modbus_tcp as modbus_tcp


q = queue.Queue(2)
t1 = 0

class NotificationDelegate(DefaultDelegate):
    def __init__(self,):
        global flag
        DefaultDelegate.__init__(self)
        # ~ self.number = number
        # ~ self._ser = serial
        # ~ try:
        # ~ # parameter(ip/port)
            # ~ server = modbus_tcp.TcpServer(address="10.13.117.122",port=502)            ##logger.info("enter 'quit' for closing the server")			      
            # ~ server = modbus_tcp.TcpServer() 
            # ~ server.start()
            # ~ print ('server start..')
            # ~ self.slave = server.add_slave(1)
            # ~ self.slave.add_block('ro', cst.HOLDING_REGISTERS, 0, 100)
        # ~ except ValueError: 
            # ~ print('server create fail')
            # ~ server.stop()
            # ~ server._do_exit()
    def handleNotification(self, cHandle, data):
        # ~ dd = str(data,encoding="utf-8")
        # ~ print(dd)
        # ~ print(len(dd))
        print(data)
   
        #~ print( 'Connection:'+str(self.number)+'\nHandler:'+str(cHandle)+'\nMsg:'+str(data) )
        
        #~ if q.qsize()!=0:
            #~ t1 = q.get()
            #~ t2 = time.time()
        #~ else :
            #~ t1 = 0
            #~ t2 = 0
        # ~ print(data)
        # ~ raw_data = str(data,encoding="utf-8")
        # ~ raw_data = raw_data.split(',')
        # ~ for i in range(len(raw_data)):
            # ~ print(int(float(raw_data[i])*10000))
            
        # ~ self.slave.set_values('ro', 0, int(float(raw_data[0])*10000))
        # ~ self.slave.set_values('ro', 1, int(float(raw_data[1])*10000))
        # ~ self.slave.set_values('ro', 2, int(float(raw_data[2])*10000))
        
        
        #self.slave.set_values('ro', 0, raw_data)
        #print(raw_data)

        #~ print( 'sensor:'+str(self.number+1)+','+'Msg: '+str(data,encoding="utf-8"))
        #~ self.slave
        #~ print(t2-t1)



scanner = Scanner(0)
flag = 0
class ConnectionHandlerThread (threading.Thread):
    def __init__(self, id,name,mac):
        threading.Thread.__init__(self)
        global flag
        self._mac = mac
        self._id = id
        self._name = name

    def run(self):
        p = Peripheral(self._mac)
        p.setMTU(512)
        p.setDelegate(NotificationDelegate())
        # ~ w = p.getCharacteristics(uuid='0000fff1-0000-1000-8000-00805f9b34fb')[0]
        
        # ~ w = p.getCharacteristics(uuid='0000fe40-cc7a-482a-984a-7f2ed5d3e58f')[0]
        
        # ~ notify = connection.getCharacteristics(uuid='0000fff4-0000-1000-8000-00805f9b34fb')[0]
        # ~ notify = p.getCharacteristics(uuid='0000FE42-8E22-4541-9D4C-21EDAE82ED19')[0]
        # ~ notify_handle = notify.getHandle() + 1
        # ~ p.writeCharacteristic(notify_handle, b"\x01\x00",withResponse=True)
        
 
        
        while True:  
            # ~ print(notify.read())

            # ~ print('OK')      
            #~ if connection.waitForNotifications(0.001):
                #~ t1 = time.time()
                #~ if q.qsize()==0:
                    #~ q.put(t1)
            if p.waitForNotifications(1):
                continue 
            # ~ time.sleep(1)

                
   
threadingDict = {}
bt_addrs = []
maclist=[]
connection_threads = []
       
def Scan_device():
    global connection_threads
    flag = 0
    devices = scanner.scan(2.0)
    print("[INFO] Device Name :\n")
    #scan device
    for dev in devices:
        for (adtype, desc, value) in dev.getScanData():
            if desc =="Complete Local Name":
                flag = flag +1
                print("%s)%s (mac:%s)"%(flag,value,dev.addr))
                bt_addrs.append(dev.addr)
                
    ch_number = list(input('\nChoose device number (or close-> Ctrl+C): '))
    length = len(ch_number)
    for i in range(length):
        if int(ch_number[i])>flag:
            print("\n[ERROR]exceed the range")
            exit()

    # listen device and start thread
    for i in range(length):
        id = i
        threadname = 'Ble' + str(i)
        mac = bt_addrs[int(ch_number[i])-1]
        locals()['sensor%s'%i] = Threadmanager(id,threadname,mac)
        # ~ globals()['dict%s'%i] = {"name":threadname,'mac':mac} 
        t = ConnectionHandlerThread(id,threadname,str(mac))
        maclist.append(str(mac))
        connection_threads.append(t)
        t.start()
    while True:
        try:
            # ~ print('#########',len(connection_threads))
            for i in range(len(connection_threads)):
                # ~ print(connection_threads[i].is_alive())
                if connection_threads[i].is_alive():
                    pass
                    # ~ print(connection_threads[i]) 
              
                else:
                    print("[FAIL = %s] "%i)
                    connection_threads.remove(connection_threads[i])
                    # ~ name = globals()['dict'+str(i)]['name']
                    # ~ mac = globals()['dict'+str(i)]['mac']
                    # ~ t = ConnectionHandlerThread(i,"Ble"+str(i),str(mac))
                    t = ConnectionHandlerThread(i,locals()['sensor%s'%i]._name,locals()['sensor%s'%i]._mac)
                    connection_threads.insert(i,t)
                    t.start()   
            
        except:
            print("error")
        time.sleep(2)

class Threadmanager():
    def __init__(self, id,name,mac):
        self._id = id
        self._name = name
        self._mac = mac
        

 
def state():
    global connection_threads
    while True:
        try:
            if len(connection_threads)>0:
                # ~ print('#########',len(connection_threads))
                for i in range(len(connection_threads)):
                    # ~ print(connection_threads[i].is_alive())
                    if connection_threads[i].is_alive():
                        # ~ print(connection_threads[i]) 
                        pass
                  
                    else:
                        print("[FAIL = %s] "%i)
                        connection_threads.remove(connection_threads[i])
                        name = globals()['dict'+str(i)]['name']
                        mac = globals()['dict'+str(i)]['mac']
                        t = ConnectionHandlerThread(i,"Ble"+str(i),str(mac))
                        connection_threads.insert(i,t)
                        t.start()   
            
        except:
            print("error")
        time.sleep(2)
    
    

if __name__ == "__main__":   

    Scan_device() 


    
