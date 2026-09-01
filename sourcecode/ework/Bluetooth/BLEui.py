
from MGRUI_v3 import Ui_MainWindow
from PyQt5 import QtCore, QtGui, QtWidgets
from PyQt5.QtWidgets import QTableWidgetItem,QHBoxLayout,QWidget,QVBoxLayout,QCheckBox,QFileDialog
from PyQt5.QtCore import Qt,pyqtSignal
import sys
from configparser import ConfigParser
import os
import serial
from xmodem import XMODEM
import time
import threading
from bluepy.btle import Scanner
import signal
import ctypes
import inspect


fileConfig = "./conf/config.ini"

class MainWin(QtWidgets.QMainWindow,Ui_MainWindow):
    def __init__(self):
        super(MainWin, self).__init__()
        self.setupUi(self)
        self.cfg = configsetup()
        self.tableWidget.setEditTriggers(QtWidgets.QTableWidget.NoEditTriggers)
        self.scanbtn.clicked.connect(self.online)
        self.addbtn.clicked.connect(self.add)
        self.rmbtn.clicked.connect(self.deldev)
        self.updatebtn.clicked.connect(self.update)
        self.pathbtn.clicked.connect(self.pathsource)
        self.sbtn.clicked.connect(self.scan)
        self.addbtn.setEnabled(False)
        self.rmbtn.setEnabled(False)
        self.updatebtn.setEnabled(False)
        self.pathbtn.setEnabled(False)
        

    def online(self):
        
        device_list = self.cfg.load('device')
        self.tableWidget.setRowCount(0)
        for d in device_list:
            device = d.split(';')
            id = str(device[0])
            name = device[1]
            mac = device[2]
            rowPosition = self.tableWidget.rowCount()
            self.tableWidget.insertRow(rowPosition)
            qwidget = QWidget()
            checkbox = QCheckBox()
            checkbox.setCheckState(Qt.Unchecked)
            qhboxlayout = QHBoxLayout(qwidget)
            qhboxlayout.addWidget(checkbox)
            qhboxlayout.setAlignment(Qt.AlignCenter)
            qhboxlayout.setContentsMargins(0, 0, 0, 0)
            self.tableWidget.setCellWidget(rowPosition, 0, qwidget)
            for i in range(3):  
                item = QTableWidgetItem(device[i])
                item.setTextAlignment(Qt.AlignCenter)
                self.tableWidget.setItem(rowPosition ,i+1, item)
        self.addbtn.setEnabled(True)
        self.rmbtn.setEnabled(True)
        self.pathbtn.setEnabled(True)
        self.sbtn.setEnabled(False)
        
        
    def add(self):
        temp=[]
        mactemp = []
        id  = self.idedit.text()
        name = self.nameedt.text()
        mac = self.macedt.text()
        rowPosition = self.tableWidget.rowCount()
        device = [id,name,mac]
        if len(name)!=0 and len(mac)!=0 and len(id)!=0:
            for r in range(rowPosition):
                temp.append(self.tableWidget.item(r,1).text())
                mactemp.append(self.tableWidget.item(r,3).text())
            if id not in temp and mac not in mactemp:   
                self.cfg.cfg.read(fileConfig)   
                self.tableWidget.insertRow(rowPosition)
                qwidget = QWidget()
                checkbox = QCheckBox()
                checkbox.setCheckState(Qt.Unchecked)
                qhboxlayout = QHBoxLayout(qwidget)
                qhboxlayout.addWidget(checkbox)
                qhboxlayout.setAlignment(Qt.AlignCenter)
                qhboxlayout.setContentsMargins(0, 0, 0, 0)
                self.tableWidget.setCellWidget(rowPosition, 0, qwidget)
                for i in range(3):  
                    item = QTableWidgetItem(device[i])
                    item.setTextAlignment(Qt.AlignCenter)
                    self.tableWidget.setItem(rowPosition ,i+1, item)
                
                self.textBrowser.append("[INFO] Add device (ID : {0} , Name : {1} ,Mac : {2})".format(id,name,mac))
                self.cfg.cfg.set('device','s%s'%id,str(id)+";"+str(name)+";"+str(mac))
                self.cfg.cfg.set('Modify_flag','mflag',"change")
                self.cfg.save()
                self.nameedt.clear()
                self.macedt.clear()
                self.idedit.clear()
            else:
                self.textBrowser.append("[INFO] Device ID or MAC already exist")
                        
    def deldev(self):
        self.cfg.cfg.read(fileConfig)
        cnt = 0
        for key in self.cfg.cfg["device"]:
            if self.tableWidget.cellWidget(cnt, 0).findChild(type(QCheckBox())).isChecked():
                i,n,m = self.cfg.cfg["device"][key].split(";")
                del self.cfg.cfg["device"][key]
                self.textBrowser.append("[INFO] Delete device ( ID: {0} Name : {1} ,Mac : {2})".format(i,n,m))
            cnt +=1 

        self.cfg.cfg.set('Modify_flag','mflag',"change")
        self.cfg.save() 
        self.online()
    
    def scan(self):
        self.textBrowser.append("[Scaning] Device Name :")  
        self.t =  Threadmgr([],)
        self.t.scansig.connect(self.setscanvalue)
        self.t.start()

    def pathsource(self):
        self.absolute_path = QFileDialog.getOpenFileName(self, 'Open file','./Bin',"txt files (*.bin)")
        if self.absolute_path:
            self.absolute_path = self.absolute_path[0]
            self.relative_path = self.absolute_path.split('/')
            self.relative_path = self.relative_path[-1]
            self.source.setText(self.relative_path)
            self.updatebtn.setEnabled(True)
    def update(self):
        self.cfg.cfg.read(fileConfig)
        threadlist = []
        cnt = 0
        for key in self.cfg.cfg["device"]:
            if self.tableWidget.cellWidget(cnt, 0).findChild(type(QCheckBox())).isChecked():
                i,n,m = self.cfg.cfg["device"][key].split(";")
                information = [i,n,m,cnt] #d = i-1
                print(information)
                self.updatebtn.setEnabled(False)
                self.rmbtn.setEnabled(False)
                self.addbtn.setEnabled(False)
                self.scanbtn.setEnabled(False)
                for col in range(self.tableWidget.columnCount()-1):
                    self.tableWidget.item(cnt,col+1).setBackground(QtGui.QColor(255,0,0))
                
                t = IAP(self.absolute_path,information)
                threadlist.append(t)
            cnt+=1
                
        self.tmg =  Threadmgr(threadlist,)
        self.tmg.updated.connect(self.setFinshValue)
        self.tmg.Rtbtn.connect(self.Rtbutton)
        self.tmg.start_sig.connect(self.setSartValue)
        self.tmg.start()
        
    def setSartValue(self,inf):
        self.textBrowser.append("[INFO] Updating device ( ID: {0} Name : {1} ,Mac : {2}) ".format(inf[0],inf[1],inf[2]))
        self.cfg.cfg.set("device","s%s"%inf[0],"%s;update;random"%inf[0])
        self.cfg.cfg.set('Modify_flag','mflag',"change")
        self.cfg.save()

    def setFinshValue(self,inf):
        self.cfg.cfg.read(fileConfig)
        self.cfg.cfg.set("device","s%s"%inf[0],"%s;%s;%s"%(inf[0],inf[1],inf[2]))
        self.cfg.cfg.set('Modify_flag','mflag',"change")
        self.cfg.save() 
        
        self.tableWidget.cellWidget(int(inf[3]), 0).findChild(type(QCheckBox())).setCheckState(Qt.Unchecked)        
        for col in range(self.tableWidget.columnCount()-1):
            self.tableWidget.item(int(inf[3]),col+1).setBackground(QtGui.QColor(255,255,255))
        self.textBrowser.append("[INFO] Update device {0} ( ID: {1} Name : {2} ,Mac : {3}) ".format(inf[4],inf[0],inf[1],inf[2]))
        
    def setscanvalue(self,devices):
        flag = 0
        for dev in devices:
            for (adtype, desc, value) in dev.getScanData():
                if desc =="Complete Local Name":
                    flag = flag +1
                    self.textBrowser.append("{0}){1} (mac: {2} ) ".format(flag,value,dev.addr))
    def Rtbutton(self):
        self.updatebtn.setEnabled(True)
        self.rmbtn.setEnabled(True)
        self.addbtn.setEnabled(True)
        self.scanbtn.setEnabled(True)
        
class Threadmgr(QtCore.QThread):
    start_sig = pyqtSignal(list)
    updated = pyqtSignal(list)
    Rtbtn = pyqtSignal()
    scansig = pyqtSignal(object)
    def __init__(self,tlist):
        super(Threadmgr,self).__init__()
        self.Tlist = tlist
    def run(self):
        if len(self.Tlist)!=0:
            for t in self.Tlist:
                
                tout = threading.Thread(target=timeout,args=(t,))
                self.start_sig.emit(t.inf)
                t.start()
                t.join()
                tout.start()
               
                if t.upflg==True:
                    t.inf.append("Successful")
                    self.updated.emit(t.inf)
                else:
                    t.inf.append("Fail")
                    self.updated.emit(t.inf)
                time.sleep(5)                                       
            self.Rtbtn.emit()
        else:
            self.scandev()
    def scandev(self):
        scanner = Scanner(0)
        devices = scanner.scan(3.0)
        self.scansig.emit(devices)

class IAP(threading.Thread):
    def __init__(self,file,inf):
        threading.Thread.__init__(self)
        self.conflag = True
        self._file = file
        self.inf = inf
        self.upflg = False

    @classmethod    
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
        global check
        self.connect()
        con = True
        cnt = 0
        try:
            while self.conflag:
                mactf = self.inf[2].replace(":","")
                self.ser.write(b'AT+DCON=1\r\n')
                time.sleep(0.5)
                self.ser.write(('AT+CON='+str(mactf)+'\r\n').encode())
                check = True
                print("try to connect")
                receive = self.ser.readline().decode()
                print(receive)
                check = False
                        
                if receive == '+Connect Failed\r\n' or receive == '+CON Error!\r\n' or len(receive)==0:
                    print("Connect Failed")
                    cnt+=1
                    if cnt >2:
                        self.upflg = False
                        
                        rst = False
                        print("BT connect fail")
                        #~ raise Exception
                        break
                if receive == '+MTU:244\r\n':
                    print("BT connect")
                    cnt=0
                    self.conflag = False
                    rst=True
                    time.sleep(0.1)
                    self.ser.write(b'request\r\n')
                    while rst:
                        check = True
                        receive = self.ser.readline().decode()
                        print(receive) 
                        check = False
                        if receive == 'RESTART\r\n':
                            time.sleep(0.5)
                            self.ser.write(b'request')
                            print("mcu restart")
                            rst = False
                            iap = True
                            
                            while iap:
                                check = True
                                receive = self.ser.readline().decode()
                                print(receive) 
                                check = "bbk"
                                if receive =="IAP processing\r\n" :
                                    iap=False
                                    modem = XMODEM(self.getc, self.putc,size = 128,mode='ymodem')
                                    aa = modem.send(self._file)
                                    self.ser.write(b'AT+DCON=1\r\n')
                                    self.upflg = True
                                    print('IAP Finish')
                                    break   

        except KeyboardInterrupt:
            if serial != None:
                serial.close()


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
    
    
def timeout(dev):
    global check
    timeout = 10
    time_trg = True
    while True:
        if check:
            if time_trg:
                t1 = time.time()
                time_trg = False
            else :
                if (time.time()>t1+timeout):
                    print("timeout")
                    time_trg = True
                    check = False
                    stop_thread(dev)
                    del dev
                    break
        if check =="bbk":
            break
        time.sleep(0.1)

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
             
             
if __name__ == "__main__":
    app = QtWidgets.QApplication(sys.argv)
    window = MainWin()
    window.show()
    sys.exit(app.exec_())
