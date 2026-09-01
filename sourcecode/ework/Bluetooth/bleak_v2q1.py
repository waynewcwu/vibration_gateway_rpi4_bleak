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
#####################################################################
# Date : 20240417 (Modify by Wayne)
# Content :
# 1. Replace bluepy module to Bleak module
# 2. Add delay time wait & check bluetooth module of rpi
# 3. Remove WARNING level log of asynico & bluez
# 4. Add "Ctrl + C" KeyboardInterrupt function for Bleak async execution
#####################################################################
# Date : 20250505 (Modify by Wayne)
# Content :
# 1.Bleak update
# 2. modify connect method to fit HTI ble module
####################################################################
#####################################################################
# Date : 202605xx (Modify by Wayne)
# Content :
# 1. Keep original Bleak_V2 logic
# 2. Improve BLE reconnect stability
# 3. Auto clear stale BLE connections
# 4. Parse CSV float data only
# 5. Fix Modbus register overflow
# 6. Add log rate limiting
# 7. Reduce system workload
#####################################################################
# Date : 20260624 Wayne v2q1
# Content : 
# - Keep original V2 BLE connect workflow.
# - Use direct connect first and active scan fallback.
# - Add direct-connect watchdog to avoid stuck connections.
# - Clean only the target MAC after direct-connect timeout.
# - Keep scanner-running active connect behavior.
# - Add SIGTERM/systemd restart cleanup.
# - Wait for GATT service discovery before reading services.
# - Add fast Modbus offline exception response.
# - Accept UTF-8 CSV float BLE data only.
#####################################################################
#-------------------------------------------------------------------------- 20230313 Wayne
import asyncio
from bleak import BleakClient, BleakScanner
import signal
import sys
import os
import subprocess
import random
import struct
from concurrent.futures import ThreadPoolExecutor
#-------------------------------------------------------------------------
import threading
import time
from configparser import ConfigParser
import logging
from logging.handlers import TimedRotatingFileHandler
# ~ logging.getLogger('werkzeug').disabled=True
import datetime
import gc
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


#-------------------------------------------------------------------------- 20250617 Wayne
# Rate limit repeated logs to reduce SD card writes.
class RepeatedLogRateLimitFilter(logging.Filter):
    def __init__(self):
        super().__init__()
        self._state = {}

    def _make_key(self, msg):
        import re

        m = re.search(r"Slave\s+(\d+)\s+doesn't exist", msg)
        if m:
            return "slave_missing:%s" % m.group(1)

        m = re.search(
            r"\[BLE\]\[CONNECT_LEGACY_FAIL\].*?SENSOR ID:(\d+).*?MAC:([^,\s]+)",
            msg
        )
        if m:
            return "legacy_fail:%s:%s" % (m.group(1), m.group(2))

        return None

    def filter(self, record):
        # The same LogRecord may pass through multiple handlers.
        # Reuse the first decision to avoid double counting.
        if hasattr(record, "_rate_limit_allow"):
            return record._rate_limit_allow

        msg = record.getMessage()
        key = self._make_key(msg)

        if not key:
            record._rate_limit_allow = True
            return True

        now = time.time()
        state = self._state.setdefault(
            key,
            {
                "normal_count": 0,
                "rate60_count": 0,
                "last_log_time": 0,
            }
        )

        # First 3 logs: keep original message.
        if state["normal_count"] < 3:
            state["normal_count"] += 1
            state["last_log_time"] = now
            record._rate_limit_allow = True
            return True

        # Next 60 logs: write at most once per 60 seconds.
        if state["rate60_count"] < 60:
            if now - state["last_log_time"] >= 60:
                state["rate60_count"] += 1
                state["last_log_time"] = now
                record.msg = "[RATE:60s] " + msg
                record.args = ()
                record._rate_limit_allow = True
                return True

            record._rate_limit_allow = False
            return False

        # After 60 rate-limited logs: write at most once per hour.
        if now - state["last_log_time"] >= 3600:
            state["last_log_time"] = now
            record.msg = "[RATE:1h] " + msg
            record.args = ()
            record._rate_limit_allow = True
            return True

        record._rate_limit_allow = False
        return False

#--------------------------------------------------------------------------

log_filename = datetime.datetime.now().strftime("./log/%Y-%m-%d_%H_%M.log")

# INFO keeps lifecycle/errors in the file while excluding high-frequency
# reconnect bookkeeping, which is logged at DEBUG.
logging.basicConfig(level=logging.INFO,
                    format='%(asctime)s %(name)-12s %(levelname)-8s %(message)s',
                    handlers = [TimedRotatingFileHandler(filename =log_filename ,when="D",interval=1,backupCount=7)]
                    )

console = logging.StreamHandler()
console.setLevel(logging.INFO)
formatter = logging.Formatter('%(name)-12s: %(levelname)-8s %(message)s')
console.setFormatter(formatter)
logging.getLogger('').addHandler(console)

# Apply rate limit to both file and console handlers.
_repeated_log_filter = RepeatedLogRateLimitFilter()
for _handler in logging.getLogger('').handlers:
    _handler.addFilter(_repeated_log_filter)

# Reduce file-log noise from expected offline/retry state. Keep important
# connection lifecycle messages, but do not fill daily log files with retry
# bookkeeping. Console still follows its handler level and explicit log levels.
class FileNoiseFilter(logging.Filter):
    _drop_patterns = (
        '[BLE][CONNECT_LEGACY]',
        '[BLE][CONNECT_LEGACY_FAIL]',
        '[BLE][SCAN]',
        '[BLE][FOUND]',
        '[BLE][CONNECT_ACTIVE_START]',
        '[BLE][CONNECT]',
        '[BLE][DISCONNECT]',
        '[BLE][DEEP_CLEAN]',
        '[BLE][RETRY_WAIT]',
        '[BLE][SCAN_SKIP]',
        '[BLE][SCAN_GAP_WAIT]',
        '[BLE][CHAR]',
        '[BLE][SUBSCRIBE]',
        '[MODBUS][STALE_OFF]',
    )

    def filter(self, record):
        msg = record.getMessage()
        return not any(p in msg for p in self._drop_patterns)

_file_noise_filter = FileNoiseFilter()
for _handler in logging.getLogger('').handlers:
    if isinstance(_handler, TimedRotatingFileHandler):
        _handler.addFilter(_file_noise_filter)
#-------------------------------------------------------------------------- 20230313 Wayne   
# set asyncio log level
logging.getLogger('asyncio').setLevel(logging.WARNING)
 
# set bleak log level
logging.getLogger('bleak').setLevel(logging.WARNING)

# set modbus_tk log level
logging.getLogger("modbus_tk").setLevel(logging.CRITICAL)

#time delay to wait BLE module start  
time.sleep(8)

logging.info("Ble Version : Bleak_V2q1")
#--------------------------------------------------------------------------   

online_device=[]
connection_threads = []
connection_threads_lock = threading.RLock()
fileConfig = "./conf/config.ini"
SERVICE_STOP_WAIT_TIMEOUT = 3.0
SERVICE_BLUEZ_DISCONNECT_TIMEOUT = 2.0
SERVICE_BLUEZ_SETTLE_TIME = 1.0
SERVICE_BLUEZ_WORKERS = 8
_cleanup_lock = threading.Lock()
_cleanup_started = False
_active_toplayer = None

#-------------------------------------------------------------------------- 20260618 / 20260624 BLE timing patch
# Keep the original working BLE connect timing for multi-device restart:
# direct connect first, active scan fallback, no startup controller disconnect.
# Direct connect is bounded by a per-device watchdog so a single thread cannot
# stay stuck forever before active scan fallback.
BLE_SCAN_TIMEOUT = 20.0         # original scan window; restart recovery can need more than 4s
BLE_LEGACY_CONNECT_TIMEOUT = 20.0  # Bleak's own timeout; direct watchdog is shorter and cleaned per-MAC
BLE_ACTIVE_CONNECT_TIMEOUT = 30.0  # restore original active-scan connect timeout
BLE_DIRECT_CONNECT_WATCHDOG = 8.0  # after this, clean only this MAC and use active scan fallback
BLE_BLUEZ_BUSY_SETTLE_DELAY = 2.0  # BlueZ accepted another connect/discovery transaction; back off briefly.
BLE_SERVICE_DISCOVERY_TIMEOUT = 6.0
NOTIFY_STALE_TIMEOUT = 15.0     # connected but no notification received for this many seconds = treat data as stalled

BLE_RETRY_DELAY_MIN = 4.0
BLE_RETRY_DELAY_MAX = 6.0
BLE_OFFLINE_SUMMARY_INTERVAL = 10 * 60.0

#-------------------------------------------------------------------------- 20260618 Wayne
# Modbus stale/remove policy after BLE disconnect.
# Short disconnect: keep slave, but write a stale marker register so the
# Modbus master can know this slave is temporarily offline.
# Long disconnect: delete slave, so Modbus master gets "Slave X doesn't exist"
# instead of reading old frozen values forever.
MODBUS_STALE_REGISTER_ADDR = 49       # 0-based address, last register of 50-register block
MODBUS_STALE_ON_VALUE = 1             # 1 = stale / BLE offline
MODBUS_STALE_OFF_VALUE = 0            # 0 = fresh / BLE online
#--------------------------------------------------------------------------
def _get_retry_delay():
    return random.uniform(BLE_RETRY_DELAY_MIN, BLE_RETRY_DELAY_MAX)

def _is_bluez_busy_error(error_text):
    return (
        "InProgress" in error_text
        or "Operation already in progress" in error_text
    )
#--------------------------------------------------------------------------

# logging disconnect
isRecord = 0
record_file = "./log/BLEconnect_%s.csv"%datetime.datetime.now().strftime("%Y-%m-%d_%H_%M")
csv_header=[]

def record_BLEconnect(header,data):
    with open(record_file,'a+') as csvfile:
        writer = csv.DictWriter(csvfile,fieldnames=csv_header)
        writer.writerow({header:data})
       
def _shutdown_disconnect_if_connected(threads):
    """
    Shutdown-only safety net.

    Do not run this at startup. During service restart, startup disconnects made
    multi-device tests fail with InProgress/Timeout. At shutdown, only
    disconnect links that BlueZ still reports as connected after the owning
    Bleak loops have had a chance to disconnect.
    """
    def _disconnect(thread):
        try:
            info = subprocess.run(
                ['bluetoothctl', 'info', thread._mac],
                stdout=subprocess.PIPE,
                stderr=subprocess.DEVNULL,
                timeout=SERVICE_BLUEZ_DISCONNECT_TIMEOUT
            )
            if b'Connected: yes' not in info.stdout:
                return False

            subprocess.run(
                ['bluetoothctl', 'disconnect', thread._mac],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                timeout=SERVICE_BLUEZ_DISCONNECT_TIMEOUT
            )
            return True
        except Exception:
            return False

    if not threads:
        return False

    with ThreadPoolExecutor(max_workers=min(SERVICE_BLUEZ_WORKERS, len(threads))) as executor:
        results = list(executor.map(_disconnect, threads))
    disconnected_count = sum(1 for result in results if result)
    if disconnected_count:
        logging.info("[SERVICE][BLUEZ_DISCONNECT] ConnectedLinks:%s", disconnected_count)
    return disconnected_count > 0


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
            parsed_devices = [d.split(';') for d in devices]

            # Register every configured ID first. The Modbus master may poll all
            # IDs while BLE threads are still starting one by one.
            if hasattr(self.mdl, "register_configured_client"):
                for device in parsed_devices:
                    self.mdl.register_configured_client(int(device[0]))

            for d, device in zip(devices, parsed_devices):
                id = int(device[0])
                threadname = device[1]
                mac = device[2]
                if(threadname not in csv_header):
                    csv_header.append(threadname)

                with connection_threads_lock:
                    if any(t._id == id and t.is_alive() for t in connection_threads):
                        continue

                t = ConnectionHandlerThread(self.mdl,device)
                logging.info("[SETUP][ADD] SENSOR ID:%s Name:%s MAC:%s"%(id,threadname,mac))
                with connection_threads_lock:
                    online_device.append(d)
                    connection_threads.append(t)
                t.start()
                # Keep original startup pacing. Starting many BLE threads too
                # quickly made service restart prone to BlueZ InProgress/Timeout.
                time.sleep(1.0)
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
                id = int(device[0])

                with connection_threads_lock:
                    targets = [t for t in connection_threads if t._id == id]
                    for t in targets:
                        t.ifdo = False
                        connection_threads.remove(t)
                    if d in online_device:
                        online_device.remove(d)

                if hasattr(self.mdl, "unregister_configured_client"):
                    self.mdl.unregister_configured_client(id)
                try:
                    self.mdl.del_client(id)
                except Exception:
                    pass
                gc.collect()
        except:
            logging.error("[SETUP][FAIL] Del Sensor Thread Error")
            pass
     
#-------------------------------------------------------------------------- 20230313 Wayne       
#class NotificationDelegate(DefaultDelegate):
class NotificationDelegate:
#-------------------------------------------------------------------------- 
    def __init__(self, sid,name,mdl):
        self._id = sid  
        self._name = name
        self._mdl = mdl
        globals()['datam%s'%self._id]  = Data()
#-------------------------------------------------------------------------- 20230313 Wayne
    def handleNotification(self, cHandle, data):               
    #async def handleNotification(self, cHandle, data):
#--------------------------------------------------------------------------   
        raw_data = str(data,encoding="utf-8")
        #logging.warning("[SaveID]: %s, [DATA]: %s " % (str(self._id), raw_data)) #20230313 Wayne
        #print("[SaveID]: %s, [DATA]: %s " % (str(self._id), raw_data)) #20230313 Wayne
        strlist = raw_data.split(',')
        self._mdl.send(str(self._id),self._name,strlist)
"""        
##############################
# BlueTooth connect function #      
##############################
"""        
           
class ConnectionHandlerThread (threading.Thread):
    def __init__(self,mdl,device):
        threading.Thread.__init__(self, daemon=True)
        self._id = int(device[0])
        self._name = device[1]
        self._mac = device[2].strip()
        global isRecord
        self.ifdo = True
        self.inf = device
        self._concnt = 0
        self.mdl = mdl
        self._last_notify_ts = time.time()  # last time we got a notification; used to detect "connected but data stopped"
        self._ever_ready = False
        self._legacy_probe_due = True
        self._retry_count = 0
        self._last_offline_summary_ts = 0.0
#-------------------------------------------------------------------------- 20230313 Wayne
    def check_bluetooth_status(self):
        try:
            result = subprocess.run(
                ['hciconfig', 'hci0'],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                timeout=5
            )

            return b'UP RUNNING' in result.stdout

        except Exception as e:
            logging.warning("[BLE][HCICONFIG_FAIL] %s", str(e))
            return False

    def wait_bluetooth_ready(self):
        retry = 0

        while not self.check_bluetooth_status():
            retry += 1

            logging.warning(
                "[BLE][ADAPTER_WAIT] hci0 not ready, retry:%s",
                retry
            )

            time.sleep(8)

            if retry >= 10:
                raise Exception("Bluetooth adapter hci0 not ready")

    async def cleanup_direct_connect_timeout(self, mac):
          try:
              if hasattr(self, "client") and self.client and self.client.is_connected:
                  await self.client.disconnect()
          except Exception:
              pass

          # Direct connect timeout can leave a per-device controller operation in
          # BlueZ. Clear only this MAC, then let active scan fallback run.
          try:
              subprocess.run(
                  ['bluetoothctl', 'disconnect', mac],
                  stdout=subprocess.DEVNULL,
                  stderr=subprocess.DEVNULL,
                  timeout=1.5
              )
          except Exception:
              pass

          await asyncio.sleep(BLE_BLUEZ_BUSY_SETTLE_DELAY)

    async def connect_legacy_first(self):
          mac = self._mac.strip()

          logging.debug(
              "[BLE][CONNECT_LEGACY] SENSOR ID:%s ,Name:%s ,MAC:%s ,Timeout:%.0fs ,Watchdog:%.0fs",
              self._id,
              self._name,
              mac,
              BLE_LEGACY_CONNECT_TIMEOUT,
              BLE_DIRECT_CONNECT_WATCHDOG
          )
          
          self.client = BleakClient(mac, timeout=BLE_LEGACY_CONNECT_TIMEOUT)
          try:
              await asyncio.wait_for(
                  self.client.connect(),
                  timeout=BLE_DIRECT_CONNECT_WATCHDOG
              )
          except asyncio.TimeoutError:
              await self.cleanup_direct_connect_timeout(mac)
              raise TimeoutError("Legacy connect watchdog timeout")
          
          logging.debug(
              "[BLE][CONNECT_LEGACY_OK] SENSOR ID:%s ,Name:%s ,MAC:%s",
              self._id,
              self._name,
              mac
          )
    async def scan_and_connect_active(self):
        self.wait_bluetooth_ready()
        mac = self._mac.strip().lower()
        found_device = None
        found_event = asyncio.Event()
        found_logged = False

        def callback(device, adv):
            nonlocal found_device, found_logged

            if device.address.lower() == mac:
                # Some peripherals advertise repeatedly while we are trying to
                # connect. Record only the first FOUND log to avoid log flooding,
                # but keep the scanner running because some modules connect more
                # reliably while scanning is still active.
                if not found_logged:
                    found_logged = True
                    logging.debug(
                        "[BLE][FOUND] SENSOR ID:%s ,Name:%s ,MAC:%s ,Device:%s",
                        self._id,
                        self._name,
                        self._mac,
                        device
                    )

                found_device = device
                if not found_event.is_set():
                    found_event.set()

        scanner = BleakScanner(callback)

        logging.debug(
            "[BLE][SCAN] SENSOR ID:%s ,Name:%s ,MAC:%s",
            self._id,
            self._name,
            self._mac
        )

        # Scan gap is now enforced before acquiring the radio lock in connect_auto(),
        # so we do not hold the lock while waiting here.
        await scanner.start()

        try:
            await asyncio.wait_for(found_event.wait(), timeout=BLE_SCAN_TIMEOUT)

            if found_device is None:
                raise Exception("Target found_event set but found_device is None")

            logging.debug(
                "[BLE][CONNECT_ACTIVE_START] SENSOR ID:%s ,Name:%s ,MAC:%s",
                self._id,
                self._name,
                self._mac
            )

            self.client = BleakClient(
                found_device,
                timeout=BLE_ACTIVE_CONNECT_TIMEOUT
            )

            # Do NOT stop scanner before connect. Some modules may be found by
            # scan but fail with Device Not Found if the scanner is stopped first.
            # Let Bleak/BlueZ own the connect timeout; do not cancel externally.
            await self.client.connect(dangerous_use_bleak_cache=True)

            logging.debug(
                "[BLE][CONNECT] SENSOR ID:%s ,Name:%s ,MAC:%s",
                self._id,
                self._name,
                self._mac
            )

        finally:
            try:
                await scanner.stop()
            except Exception as e:
                logging.warning("[BLE][SCAN_STOP_FAIL] %s", str(e))

            # If connect timed out/failed after creating a client object, make sure
            # BlueZ does not keep a half-open connection object that blocks the next
            # reconnect attempt.
            try:
                if hasattr(self, "client") and self.client and not self.client.is_connected:
                    await self.client.disconnect()
            except Exception:
                pass
    
    async def connect_auto(self):
        # Match the original proven startup flow:
        # direct connect first, then active scan fallback in the same cycle.
        if self._legacy_probe_due:
            self._legacy_probe_due = False
            try:
                await self.connect_legacy_first()
                return
            except Exception as e:
                error_text = str(e) or type(e).__name__
                if _is_bluez_busy_error(error_text):
                    self._legacy_probe_due = True
                    logging.debug(
                        "[BLE][BLUEZ_BUSY] SENSOR ID:%s ,Name:%s ,MAC:%s ,RetryDirect:1 ,Error:%s",
                        self._id, self._name, self._mac, error_text
                    )
                    await asyncio.sleep(
                        BLE_BLUEZ_BUSY_SETTLE_DELAY + random.uniform(0.0, 0.5)
                    )
                    raise Exception("BlueZ busy; direct connect retry pending")

                logging.debug(
                    "[BLE][CONNECT_LEGACY_FAIL] SENSOR ID:%s ,Name:%s ,MAC:%s ,Error:%s",
                    self._id, self._name, self._mac, error_text
                )
                try:
                    if hasattr(self, "client") and self.client:
                        await self.client.disconnect()
                except Exception:
                    pass

                await asyncio.sleep(1.0)

        if not self.ifdo:
            raise Exception("Device removed before active scan")

        await self.scan_and_connect_active()
    
    
    
    def run(self):
        asyncio.run(self.connection_loop())

    async def connection_loop(self):
        try:
            while self.ifdo:
                await self.async_run()
        finally:
            # The client belongs to this event loop; disconnect it here.
            try:
                if hasattr(self, "client") and self.client and self.client.is_connected:
                    await self.client.disconnect()
            except Exception:
                pass

    async def get_services_ready(self):
        last_error = None

        for _ in range(3):
            try:
                services = self.client.services
                if services is not None:
                    return services
            except Exception as e:
                last_error = e

            try:
                get_services = getattr(self.client, "get_services", None)
                if callable(get_services):
                    services = await asyncio.wait_for(
                        get_services(),
                        timeout=BLE_SERVICE_DISCOVERY_TIMEOUT
                    )
                    if services is not None:
                        return services
            except Exception as e:
                last_error = e

            await asyncio.sleep(0.5)

        if last_error is not None:
            raise Exception(str(last_error) or type(last_error).__name__)

        raise Exception("Service discovery not ready")
        
    async def async_run(self):
      session_ready = False
      try:
          await self.connect_auto()
  
          await asyncio.sleep(1.0)

          services = await self.get_services_ready()

          # Create/reuse the register block before subscribing. Some peripherals
          # notify immediately inside start_notify(); without this ordering the
          # first packet races with Modbus slave creation.
          try:
              build_result = self.mdl.build_client(self._id, online=False)
          except TypeError:
              # Preserve compatibility with Restful/Mqtt implementations.
              build_result = self.mdl.build_client(self._id)

          if not self.ifdo or build_result is False:
              try:
                  if self.client.is_connected:
                      await self.client.disconnect()
              except Exception:
                  pass
              return
  
          subscribe_count = 0

          for service in services:
              for characteristic in service.characteristics:
                  props = characteristic.properties
                  uuid = characteristic.uuid.lower()
          
                  logging.debug(
                      "[BLE][CHAR] SENSOR ID:%s Char:%s Properties:%s",
                      self._id,
                      characteristic.uuid,
                      props
                  )
          

                  if "notify" in props:
                      await self.client.start_notify(
                          characteristic.uuid,
                          self.notification_handler
                      )
          
                      subscribe_count += 1
          
                      logging.debug(
                          "[BLE][SUBSCRIBE] SENSOR ID:%s UUID:%s Properties:%s",
                          self._id,
                          characteristic.uuid,
                          props
                      )
  
          if subscribe_count == 0:
              raise Exception("No notify characteristic found")

          if hasattr(self.mdl, "set_client_online"):
              self.mdl.set_client_online(self._id, True)
          session_ready = True
          self._ever_ready = True
          self._legacy_probe_due = True
          self._retry_count = 0
          self._last_offline_summary_ts = 0.0
        
          logging.info(
              "[BLE][READY] SENSOR ID:%s ,Name:%s ,MAC:%s ,SubscribeCount:%s",
              self._id,
              self._name,
              self._mac,
              subscribe_count
          )
  
          disconnect_count = 0
          self._last_notify_ts = time.time()  # reset before monitoring starts, so the wait before subscribing isn't mistaken for stalled data
  
          while self.ifdo:
              await asyncio.sleep(0.5)
  
              if not self.client.is_connected:
                  disconnect_count += 1
                  if disconnect_count > 6:
                      raise Exception("BLE disconnected")
                  continue
  
              disconnect_count = 0
  
              # is_connected only reflects the connection layer; it does not guarantee
              # notifications are still being delivered. Also check how long since the
              # last notification, to catch a peripheral that froze or a notify
              # subscription that silently stopped working, so the Modbus register
              # doesn't stay stuck on stale values with no warning at all.
              stale_seconds = time.time() - self._last_notify_ts
              if stale_seconds > NOTIFY_STALE_TIMEOUT:
                  raise Exception(
                      "BLE connected but no notification received for %.0fs" % stale_seconds
                  )

          # Configuration removed this device. Exit without creating a
          # replacement thread; the manager already removed its Modbus ID.
          try:
              if hasattr(self, "client") and self.client and self.client.is_connected:
                  await self.client.disconnect()
          except Exception:
              pass

      except Exception as e:
          # Service/config shutdown is intentional, not an offline retry.
          if not self.ifdo:
              try:
                  if hasattr(self, "client") and self.client and self.client.is_connected:
                      await self.client.disconnect()
              except Exception:
                  pass
              return

          self._retry_count += 1
          now = time.time()
          error_text = str(e) or type(e).__name__

          if session_ready:
              logging.warning(
                  "[BLE][OFFLINE] SENSOR ID:%s Name:%s MAC:%s Error:%s",
                  self._id, self._name, self._mac, error_text
              )
          elif (
              self._last_offline_summary_ts == 0.0
              or now - self._last_offline_summary_ts >= BLE_OFFLINE_SUMMARY_INTERVAL
          ):
              logging.info(
                  "[BLE][OFFLINE_RETRY] SENSOR ID:%s Name:%s MAC:%s Attempts:%s LastError:%s",
                  self._id, self._name, self._mac, self._retry_count, error_text
              )
              self._last_offline_summary_ts = now
  
          if isRecord and session_ready:
              record_BLEconnect(
                  self._name,
                  datetime.datetime.now().strftime("%Y-%m-%d_%H:%M:%S")
              )
  
          try:
              if hasattr(self, "client") and self.client:
                  if self.client.is_connected:
                      await self.client.disconnect()
          except Exception as de:
              logging.warning("[BLE][DISCONNECT_FAIL] %s", str(de))

          # FastOfflineDatabank immediately returns exception 0x04 while offline.
          # Keep the existing register block; deleting it is unnecessary and old
          # delete timers could race with a successful reconnect.
          try:
              if hasattr(self.mdl, "set_client_online"):
                  self.mdl.set_client_online(self._id, False)
          except Exception as me:
              logging.warning(
                  "[MODBUS][DISCONNECT_POLICY_FAIL] Slave:%s Error:%s",
                  self._id,
                  str(me)
              )
  
          if not self.ifdo:
              return

          if _is_bluez_busy_error(error_text):
              # Keep the next cycle on the direct-connect path. BlueZ was busy,
              # not necessarily the peripheral.
              self._legacy_probe_due = True
              retry_delay = BLE_BLUEZ_BUSY_SETTLE_DELAY + random.uniform(0.0, 0.5)
          else:
              retry_delay = _get_retry_delay()

          logging.debug(
              "[BLE][RETRY_WAIT] SENSOR ID:%s ,Name:%s ,MAC:%s ,Delay:%.1fs",
              self._id,
              self._name,
              self._mac,
              retry_delay
          )
          await asyncio.sleep(retry_delay)

    def notification_handler(self, sender, data):
        # Receiving any notification means this connection and subscription are
        # still alive, regardless of whether the payload is valid. Update the
        # timestamp first; this is what the stale-data check relies on.
        self._last_notify_ts = time.time()

        # Only accept UTF-8 ASCII CSV float data, e.g. b"25.35,88.70,0.14,...".
        # Do NOT convert hex/binary bytes to Modbus registers.
        try:
            raw_data = data.decode("utf-8", errors="strict")
            raw_data = raw_data.replace("\x00", "").strip()

            strlist = [
                item.strip()
                for item in raw_data.split(",")
                if item.strip() != ""
            ]

            if not strlist:
                return

            # Validate all fields are float values before sending to Modbus.
            for item in strlist:
                float(item)

            self.mdl.send(str(self._id), self._name, strlist)

        except Exception:
            # Ignore non-CSV / non-float / hex / binary data.
            return
#--------------------------------------------------------------------------


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
                with connection_threads_lock:
                    online = set(online_device)
                setup = set(temp)
               
                del_target = list(online.difference(setup))
                add_target = list(setup.difference(online))
                
                Tdmgr.delTd(del_target)
                Tdmgr.createTd(add_target)
                Con.cfg.set('Modify_flag','mflag',"default")
                Con.save()

                # Write backup only when configuration actually changes.
                # The previous unconditional 10-second write caused needless
                # SD-card traffic even while the configuration was idle.
                with open('./conf/backup.ini','w') as f:
                    Con.cfg.write(f)
           
        except :
            logging.warning("[CONFIG][FAIL] Reload Configure Setup Error")  
            Con= configsetup()
            Con.cfg.read('./conf/backup.ini')
            Con.cfg.set('Modify_flag','mflag',"change")
            with open('./conf/config.ini','w') as f:
                Con.cfg.write(f)
        time.sleep(2)
       
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
       
       


class FastOfflineDatabank(modbus.Databank):
    """
    Return a fast Modbus exception for unavailable Modbus slave IDs.

    modbus_tk normally returns an empty response when a slave does not exist.
    A Modbus master must then wait for its socket timeout, so sequential polling
    becomes slower for every offline or unknown slave. This databank keeps
    configuration state separate from register blocks and returns Slave Device
    Failure (0x04) immediately for:
    - configured-but-offline IDs
    - unconfigured / missing IDs
    """

    def __init__(self):
        super().__init__(error_on_missing_slave=True)
        self._configured_slave_ids = set()
        self._offline_slave_ids = set()
        self._offline_state_lock = threading.RLock()

    def register_configured_slave(self, slave_id):
        slave_id = int(slave_id)
        with self._offline_state_lock:
            self._configured_slave_ids.add(slave_id)
            self._offline_slave_ids.add(slave_id)

    def unregister_configured_slave(self, slave_id):
        slave_id = int(slave_id)
        with self._offline_state_lock:
            self._configured_slave_ids.discard(slave_id)
            self._offline_slave_ids.discard(slave_id)

    def set_slave_online(self, slave_id, online):
        slave_id = int(slave_id)
        with self._offline_state_lock:
            if slave_id not in self._configured_slave_ids:
                return
            if online:
                self._offline_slave_ids.discard(slave_id)
            else:
                self._offline_slave_ids.add(slave_id)

    def is_configured_slave(self, slave_id):
        with self._offline_state_lock:
            return int(slave_id) in self._configured_slave_ids

    def _build_slave_failure_response(self, query, request_pdu):
        function_code = struct.unpack(">B", request_pdu[0:1])[0]
        exception_pdu = struct.pack(
            ">BB",
            function_code | 0x80,
            cst.SLAVE_DEVICE_FAILURE
        )
        return query.build_response(exception_pdu)

    def handle_request(self, query, request):
        # Parse once to identify the TCP Unit ID. TcpQuery.parse_request also
        # stores the MBAP header needed by build_response().
        try:
            slave_id, request_pdu = query.parse_request(request)
            with self._offline_state_lock:
                configured = slave_id in self._configured_slave_ids
                offline = slave_id in self._offline_slave_ids

            if request_pdu and ((configured and offline) or not configured):
                return self._build_slave_failure_response(query, request_pdu)
        except Exception:
            # Preserve modbus_tk's standard invalid-request handling.
            pass

        # Online configured slaves keep normal modbus_tk behavior.
        return super().handle_request(query, request)


class Modbus(Toplayer):
    def __init__(self,ip):
        try:

            # parameter(ip/port)
            global isRecord
            self._ip = str(ip)
            #logging.info("Modbus IP:%s "%self._ip)              
            self.server = modbus_tcp.TcpServer(address = self._ip,port=502)
            # Install before server.start(), so no request can pass through the
            # default missing-slave/no-response behavior during startup.
            self.fast_offline_databank = FastOfflineDatabank()
            self.server._databank = self.fast_offline_databank
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

    def register_configured_client(self, sid):
        self.fast_offline_databank.register_configured_slave(sid)

    def unregister_configured_client(self, sid):
        self.fast_offline_databank.unregister_configured_slave(sid)

    def set_client_online(self, sid, online):
        self.fast_offline_databank.set_slave_online(sid, online)

    def build_client(self, sid, online=True):
        sid = int(sid)
        slave_key = 'slave%s' % sid

        # Config removal can happen while a BLE connect is in progress.
        # Never recreate a Modbus slave after its configured ID was removed.
        if not self.fast_offline_databank.is_configured_slave(sid):
            return False
    
        try:
            # If slave already exists in modbus_tk server, reuse it.
            try:
                globals()[slave_key] = self.server.get_slave(sid)
    
                logging.debug(
                    "[MODBUS][EXIST] Modbus Slave %s already exists, reuse it",
                    sid
                )

                self.mark_client_stale(sid, False)
                self.set_client_online(sid, online)
    
                return True
    
            except Exception:
                pass
    
            # If not exists, create new slave.
            globals()[slave_key] = self.server.add_slave(sid)
            globals()[slave_key].add_block(
                str(sid),
                cst.HOLDING_REGISTERS,
                0,
                50
            )
    
            logging.info("[MODBUS][ADD] Modbus Add Slave %s" % sid)

            self.mark_client_stale(sid, False)
            self.set_client_online(sid, online)
            return True
    
        except Exception as e:
            logging.error(
                "[MODBUS][ADD_FAIL] Slave:%s Error:%s",
                sid,
                str(e)
            )
            raise  


    def del_client(self,sid):
        sid = int(sid)
        slave_key = 'slave%s' % sid

        try:
            self.server.remove_slave(sid)
            logging.info("[MODBUS][Del] Modbus Delete Slave %s" % sid)
        except Exception as e:
            logging.debug(
                "[MODBUS][DEL_SKIP] Slave:%s Error:%s",
                sid,
                str(e)
            )

        try:
            if slave_key in globals():
                del globals()[slave_key]
        except Exception:
            pass

    def mark_client_stale(self, sid, stale=True):
        # Use the last holding register as status marker.
        # 0 = fresh/online, 1 = stale/offline.
        sid = int(sid)
        slave_key = 'slave%s' % sid

        try:
            if slave_key not in globals():
                globals()[slave_key] = self.server.get_slave(sid)

            globals()[slave_key].set_values(
                str(sid),
                MODBUS_STALE_REGISTER_ADDR,
                MODBUS_STALE_ON_VALUE if stale else MODBUS_STALE_OFF_VALUE
            )

            log_func = logging.warning if stale else logging.debug
            log_func(
                "[MODBUS][STALE_%s] Slave:%s Register:%s Value:%s",
                "ON" if stale else "OFF",
                sid,
                MODBUS_STALE_REGISTER_ADDR,
                MODBUS_STALE_ON_VALUE if stale else MODBUS_STALE_OFF_VALUE
            )

        except Exception as e:
            logging.warning(
                "[MODBUS][STALE_FAIL] Slave:%s Stale:%s Error:%s",
                sid,
                stale,
                str(e)
            )

    def send(self, sid, name, datalist):
        try:
            sid_int = int(sid)
            slave_key = 'slave%s' % sid_int
    
            if slave_key not in globals():
                globals()[slave_key] = self.server.get_slave(sid_int)
    
                logging.info(
                    "[MODBUS][GET_EXIST] Slave:%s restored from server",
                    sid
                )
    
            try:
                globals()[slave_key].set_values(
                    str(sid_int),
                    MODBUS_STALE_REGISTER_ADDR,
                    MODBUS_STALE_OFF_VALUE
                )
            except Exception:
                pass

            # Keep last register for stale status, do not overwrite it with sensor data.
            max_count = min(len(datalist), MODBUS_STALE_REGISTER_ADDR)
            for addr in range(max_count):
                try:
                    data = int(float(datalist[addr]))
                except Exception:
                    logging.warning(
                        "[MODBUS][SKIP_BAD_VALUE] Slave:%s Addr:%s Raw:%r",
                        sid,
                        addr,
                        datalist[addr]
                    )
                    continue
    
                if data >= 65535:
                    data = 65535
    
                if data < 0:
                    data = 0
    
                globals()[slave_key].set_values(
                    str(sid_int),
                    addr,
                    data
                )
                #print("ID:%s , add:%s , data:%s"%(sid,addr,data))
                 
        except Exception as e:
            logging.warning(
                "[MODBUS][FAIL] Slave:%s Send Data Error:%s DataList:%s",
                sid,
                str(e),
                datalist
            )    

           
    def on_receive(self,msgs):
        logging.debug("[Slave ID:%s] %s"%(get_log_buffer("",msgs[1][6:7]),get_log_buffer("-->",msgs[1][6:])))
        print("[Slave ID:%s] %s"%(get_log_buffer("",msgs[1][6:7]),get_log_buffer("-->",msgs[1][6:])))
    def on_response(self,msgs):
        logging.debug("[Slave ID:%s] %s"%(get_log_buffer("",msgs[1][6:7]),get_log_buffer("<--",msgs[1][6:])))
        print("[Slave ID:%s] %s"%(get_log_buffer("",msgs[1][6:7]),get_log_buffer("<--",msgs[1][6:])))
#-------------------------------------------------------------------------- 20230313 Wayne
"""        
#############################################
# cleapup BLE connection when program stop  #
#############################################
"""
def cleanup():
    global _cleanup_started

    with _cleanup_lock:
        if _cleanup_started:
            return
        _cleanup_started = True

    logging.info("[SERVICE][STOP] Fast graceful shutdown")

    # Stop Modbus first so its non-daemon server thread cannot keep Python alive.
    try:
        if _active_toplayer is not None and hasattr(_active_toplayer, "server"):
            _active_toplayer.server.stop()
    except Exception:
        pass

    with connection_threads_lock:
        threads = list(connection_threads)

    for t in threads:
        t.ifdo = False

    # Connected monitor loops wake every 0.5s and disconnect in their own loop.
    deadline = time.time() + SERVICE_STOP_WAIT_TIMEOUT
    for t in threads:
        remaining = deadline - time.time()
        if remaining <= 0:
            break
        t.join(timeout=remaining)

    # Shutdown-only controller safety net. Do not disconnect all configured
    # devices blindly; that restart-drain path made multi-device restart tests
    # fail after service restart. Only clear links still reported connected.
    disconnected_any = _shutdown_disconnect_if_connected(threads)

    if disconnected_any:
        # Let BlueZ/controller complete Disconnect before the new service starts.
        time.sleep(SERVICE_BLUEZ_SETTLE_TIME)
      
def signal_handler(sig, frame):
    logging.info("[SERVICE][SIGNAL] Received:%s", sig)
    cleanup()
    logging.shutdown()
    os._exit(0)

#--------------------------------------------------------------------------        
if __name__ == "__main__":
    # Ctrl+C sends SIGINT; systemctl stop/restart sends SIGTERM.
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
  
    # load configure and return setup ble mac

    cfg = configsetup()
    device_list = cfg.load('device')
    ip = cfg.cfg['Toplayer']['hostip']
    protocol = cfg.cfg['Toplayer']['Protocol']
    isRecord =  int(cfg.cfg['Modify_flag']['record'])
    module = locals()[protocol](ip)
    _active_toplayer = module
    Tdmgr = Threadmanager(module)
    Tdmgr.createTd(device_list)
    # To check Configure update
    th = threading.Thread(target=checkconfig,args=(module,),daemon=True)
    th.start()
    
    # keep main running
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        cleanup()
        sys.exit(0)
