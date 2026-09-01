# modify date:20200529
# Evan
## resistance 220 
import RPi.GPIO as GPIO
GPIO.setwarnings(False)
import time
import Adafruit_ADS1x15
import threading
from queue import Queue
import sys
import modbus_tk
import modbus_tk.modbus as modbus
import modbus_tk.defines as cst
import modbus_tk.modbus_tcp as modbus_tcp
import configparser
import logging
import struct
import datetime
from logging.handlers import TimedRotatingFileHandler

event = Queue(2)

#TODO: load parameter from config 
cfg=configparser.ConfigParser()
cfg.read("./config/Parameter.conf")
alarm_deltah=int(cfg.get("Water_detect","water_level"))
target_time=int(cfg.get("Water_detect","time_period"))
time_delay = 0.5
targetcount = target_time/time_delay

#TODO: logging setup parameter by date
log_filename = datetime.datetime.now().strftime("./log/%Y-%m-%d_%H_%M.log")

logging.basicConfig(level=logging.INFO,
                    format='%(asctime)s %(name)-12s %(levelname)-8s %(message)s',
                    handlers = [TimedRotatingFileHandler(filename =log_filename ,when="D",interval=1,backupCount=30)]
                    )

#~ console = logging.StreamHandler()
#~ console.setLevel(logging.INFO)
#~ formatter = logging.Formatter('%(name)-12s: %(levelname)-8s %(message)s')
#~ console.setFormatter(formatter)
#~ logging.getLogger('').addHandler(console) 

logging.info("[Setup] detetc period : "+str(target_time)+" sec")
logging.info("[Setup] water difference : "+str(alarm_deltah)+" cm")

#TODO: Listen Sensor data for 3 channel by I2C (ADS1X15) 
class Analog_Value_Thread (threading.Thread):
    def __init__(self):
        threading.Thread.__init__(self)
        self.GAIN=2/3    # Max = +6.144
        self.values = []

    def run(self):
        
        adc =Adafruit_ADS1x15.ADS1115(0x48)
        while True : 
          self.values.append(adc.read_adc(0, gain=self.GAIN))
          self.values.append(adc.read_adc(1, gain=self.GAIN))
          self.values.append(adc.read_adc(2, gain=self.GAIN))
              #~ print(self.values)
              # Send data to GPIO_Thread
          if event.empty():
              event.put(self.values)
              self.values=[]
              time.sleep(time_delay)
            
        
    

#TODO: Define GPIO pin include implement Bypass and Modbus function      
class GPIO_Thread (threading.Thread):
    def __init__(self,):
        threading.Thread.__init__(self)
        GPIO.setmode(GPIO.BCM)
        #define Control relay GPIO
        self.gpio1 = 24 #sensor1
        self.gpio2 = 25 #sensor2
        GPIO.setup(self.gpio1,GPIO.OUT,initial = GPIO.LOW)
        GPIO.setup(self.gpio2,GPIO.OUT,initial = GPIO.LOW)
        
        #define Bypass GPIO        
        GPIO.setup(18, GPIO.IN, pull_up_down = GPIO.PUD_DOWN)
        GPIO.setup(23, GPIO.IN, pull_up_down = GPIO.PUD_DOWN)
        
        #Start Analog Thread       
        senreader=Analog_Value_Thread()
        senreader.start()
        
        # initial control relay function (sensor1 and sensor2)
        self.sensor1 = control()
        self.sensor2 = control()

        self.modbus()
        
    #TODO: Create Modbus server    
    def modbus(self):
        try:           
            #server = modbus_tcp.TcpServer(address=_localip,port=_port)
            self.server = modbus_tcp.TcpServer()                  
            self.server.start()
            logging.info("Modbus server start & slave ID : 1 , Address 0 ~ 8")
            self.slave = self.server.add_slave(1)
            self.slave.add_block('ro', cst.HOLDING_REGISTERS, 0, 8)
            
        except: 
            logging.warning("Modbus server error")
            self.server.stop()
            self.server._do_exit()
    
    # Compute actual data and implement bypass function
    def run(self):
        try:
            while True:
                if not event.empty():

                    Data = event.get()
                    s1_scale = (Data[0] - 4693)/18773
                    s1_level_high = 101.79*s1_scale
                    
                    s2_scale = (Data[1] - 4693)/18773
                    s2_level_high = 101.79*s2_scale
                            
                    s3_scale = (Data[2] - 4693)/18773
                    s3_level_high = 145*s3_scale   
                            
                    s1_level = abs(round(s1_level_high,2))*100
                    s2_level = abs(round(s2_level_high,2))*100
                    s3_level = abs(round(s3_level_high,2))*100
                    # ready to sensor3
                    #~ s3_scale = (Data[2] - 4740)/18741
                    #~ s3_level_high = 101.79*s2_scale
                    self.slave.set_values('ro',0,int(s1_level))
                    self.slave.set_values('ro',1,int(s2_level))
                    self.slave.set_values('ro',2,int(s3_level))
                    
                    print("level_1 %s cm"%int(s1_level))
                    print("level_2 %s cm"%int(s2_level))
                    print("level_3 %s cm"%int(s3_level))
                    
                    if GPIO.input(18)==True:
                        self.sensor1.delta_h("s1",s1_level_high,self.gpio1)
                      
                    else :
                        print('pass1')
                        GPIO.output(self.gpio1,GPIO.LOW)
                        
                    if GPIO.input(23)==True:
                        self.sensor2.delta_h("s2",s2_level_high,self.gpio2)
                    else :
                        print('pass2')
                        GPIO.output(self.gpio2,GPIO.LOW)
                        
                time.sleep(time_delay)
        except:
          logging.warning("Data compute and control error")  
                
#TODO: Compute delta H(water level / Min) and control stop Machine        
class control():
    def __init__(self):
        self.h_init = 0 
        self.h_last = 0
        self.count = 0

        
    def delta_h(self,sensorid,data,io):
        self.count = self.count+1
        if self.count ==1 :
            self.h_init = data
            GPIO.output(io,GPIO.LOW)
            
        if self.count ==targetcount :
            self.h_last = data
            delta = self.h_init-self.h_last
            flow_rate = delta / (time_delay*self.count)
            
            self.count = 0 ; self.h_init = 0; self.h_last =0
            print('flow_rate = ',flow_rate)
            print("sensor = %s , data = %s"%(sensorid,delta))


            if delta >= alarm_deltah:
                GPIO.output(io,GPIO.HIGH)
                print('high')
          
if __name__ == '__main__':
     
    ThreadD=GPIO_Thread()
    ThreadD.start()
   
    
    
    

    

    


