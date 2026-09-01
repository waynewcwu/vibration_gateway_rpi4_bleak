import ctypes
import inspect
import time
import json

def _async_raise(tid, exctype):

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


def timeout(dev,t,wb):

    timeout = 15
    time_trg = True
    while True:
        # ~ print(t.check)
        if t.check:
            if time_trg:
                t1 = time.time()
                time_trg = False
            else :
                if (time.time()>t1+timeout):
                    print("timeout")
                    wb.server.send_message_to_all(json.dumps({"FLASHED_NG":str(dev.inf[0]),"INFO": "[WARNNING] UPDATE FAIL (TIMEOUT)"}))
                    time_trg = True
                    t.check = False
                    
                    stop_thread(dev)

                    break
        if t.check =="bbk":
            break
        time.sleep(0.1)

        
        

