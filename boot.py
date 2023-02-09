# This file is executed on every boot (including wake-boot from deepsleep)
#import esp
#esp.osdebug(None)
import uos, machine

# OTA
import network
from my_config import *
import micropython_ota

#uos.dupterm(None, 1) # disable REPL on UART(0)
import gc
#import webrepl
#webrepl.start()
gc.collect()

# connect to network
sta_if = network.WLAN(network.STA_IF)
if not sta_if.isconnected():
    print('connecting to network...')
    sta_if.active(True)
    sta_if.connect(WLAN_ID, WLAN_PASS)
    while not sta_if.isconnected():
        pass
print('network config:', sta_if.ifconfig())

# OTA
ota_host = 'http://192.168.8.110'
project_name = 'odoo_iot_mrp_control'
filenames = ['main.py', 'boot.py']

micropython_ota.ota_update(ota_host, project_name, filenames, use_version_prefix=False, hard_reset_device=True, soft_reset_device=False, timeout=5)
