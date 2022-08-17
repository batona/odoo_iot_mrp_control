# This file is executed on every boot (including wake-boot from deepsleep)
#import esp
#esp.osdebug(None)
#uos.dupterm(None, 1) # disable REPL on UART(0)
import gc
#import webrepl
#webrepl.start()
import uos
import senko
import machine
import network
from my_config import *

gc.collect()

#OTA update
OTA = senko.Senko(
  user="batona", repo="odoo_iot_mrp_control", files = ["boot.py", "main.py"]
)

#initial wifi connect
def do_connect():
    sta_if = network.WLAN(network.STA_IF)
    if not sta_if.isconnected():
        print('connecting to network...')
        sta_if.active(True)
        sta_if.connect(WLAN_ID, WLAN_PASS)
        while not sta_if.isconnected():
            pass
    print('network config:', sta_if.ifconfig())

do_connect()

if OTA.update():
    print("Updated to the latest version! Rebooting...")
    machine.reset()