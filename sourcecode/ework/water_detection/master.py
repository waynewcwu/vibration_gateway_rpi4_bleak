
import sys

#add logging capability
import logging
import time
import modbus_tk
import modbus_tk.defines as cst
import modbus_tk.modbus_tcp as modbus_tcp
import struct

logger = modbus_tk.utils.create_logger("console")

if __name__ == "__main__":
    try:
        #Connect to the slave
        master = modbus_tcp.TcpMaster(host='127.0.0.1',port=502)
        master.set_timeout(60.0)
        logger.info("connected")
        while True:
        #####master.execute("slaveid", "function","address start","address end")#######
##            for i in range(0,4): 
##                data=master.execute(10, cst.READ_HOLDING_REGISTERS,i*2,2)#, 4,data_format='>f'))
##                values=struct.unpack('>i',struct.pack('>HH', data[0], data[1]))
            # ~ for i in range(3):
                
                # ~ data1=master.execute(1, cst.READ_HOLDING_REGISTERS, 0,3)
                data2=master.execute(1, cst.READ_HOLDING_REGISTERS, 0,8)
                # ~ data2=master.execute(1, cst.READ_HOLDING_REGISTERS, 1, 2)
                # ~ print("d1:",data1)
                print("d2:",data2)
                
                time.sleep(1)
##            print(round(data[0],2))
           
        
        #send some queries
        #logger.info(master.execute(1, cst.READ_COILS, 0, 10))
        #logger.info(master.execute(1, cst.READ_DISCRETE_INPUTS, 0, 8))
        #logger.info(master.execute(1, cst.READ_INPUT_REGISTERS, 100, 3))
        #logger.info(master.execute(1, cst.READ_HOLDING_REGISTERS, 100, 12))
        #logger.info(master.execute(1, cst.WRITE_SINGLE_COIL, 7, output_value=1))
        #logger.info(master.execute(1, cst.WRITE_SINGLE_REGISTER, 100, output_value=54))
        #logger.info(master.execute(1, cst.WRITE_MULTIPLE_COILS, 0, output_value=[1, 1, 0, 1, 1, 0, 1, 1]))
        #logger.info(master.execute(1, cst.WRITE_MULTIPLE_REGISTERS, 100, output_value=xrange(12)))
        
    except modbus_tk.modbus.ModbusError as exc:
        logger.error("%s- Code=%d" % (e, e.get_exception_code()))
3
