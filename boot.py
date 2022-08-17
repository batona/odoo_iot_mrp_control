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
from machine import Pin,SPI
import utime
import network
from my_config import *

gc.collect()

#blink
def blink(n, color, duration = 0.2):
    
    led_g = Pin(13, Pin.OUT)
    led_r = Pin(12, Pin.OUT)
    led = led_g if color == 'g' else led_r
        
    led.value(0)
    while n > 0:
        n -= 1
        led.value(1)
        utime.sleep(duration)
        led.value(0)
        utime.sleep(duration)

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
