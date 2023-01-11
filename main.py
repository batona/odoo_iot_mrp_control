#
#rc522 lib: https://github.com/wendlers/micropython-mfrc522

'''
TODO
добавить приемку по rfid

CONNECTIONS
RC522    NODEMCU
-----------------
3.3V     3.3V
RST      GPIO5(D1)
GND      GND
IRQ      --
MISO     GPIO4(D2)
MOSI     GPIO2(D4)
SCK      GPIO0(D3)
SDA      GPIO14(D5)

LEDS
----------------
GREEN    GPIO13(D7)
RED      GPIO12(D6)
GND      GND
'''

from my_config import *
import network
import mfrc522
from machine import Pin,SPI
import utime
import ujson as json
import random
import urequests as requests


####################################

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
    blink(3, 'g')

def do_read():

    rdr = mfrc522.MFRC522(0, 2, 4, 5, 14)

    print("Place card")

    try:
        while True:
            (stat, tag_type) = rdr.request(rdr.REQIDL)
            if stat == rdr.OK:
                (stat, raw_uid) = rdr.anticoll()
                if stat == rdr.OK:
                    #usb reader gives uid bytes in reverse order: 3,2,1,0
                    rfid_key = "0x%02x%02x%02x%02x" %(raw_uid[3], raw_uid[2], raw_uid[1], raw_uid[0])
                    #convert to decimal
                    rfid_key = str(int(rfid_key))
                    if len(rfid_key) < 10:
                        rfid_key = '0' + rfid_key
                    print(rfid_key)
                    blink(1, 'g')
                    
                    #call to odoo server
                    do_call(rfid_key)
                    
                    #delay to prevent continious reading
                    utime.sleep(4)

    except KeyboardInterrupt:
        print("Bye")

def json_rpc(url, method, params):
    data = {
        "jsonrpc": "2.0",
        "method": method,
        "params": params,
        "id": random.getrandbits(16),
    }
    #print(data)
    
    req = requests.post(url=url, json=data)
    reply = req.json()

    if reply.get("error"):
        raise Exception(reply["error"])
    return reply["result"]

def call(url, service, method, *args):
    return json_rpc(url, "call", {"service": service, "method": method, "args": args})

def do_call(rfid_key):

    #search manufacturing order
    mo = call(url, "object", "execute", DB, uid, PASS, 'mrp.production', 'search',
              [['x_rfid_key', '=', rfid_key], ['state','not in',['done','cancel']]], 0, 1, 'id desc')
    print('mo:', mo)
    
    if mo == []:
        print('MO Not found by RFID: ' + rfid_key)
        #error_message('mrp.production', 0, 'MO Not found by RFID:' + rfid_key)
        blink(1, 'r', 1)
        return
    
    #read MO state
    r = call(url, "object", "execute", DB, uid, PASS, 'mrp.production', 'read', mo, ['name', 'state'])
    #print(r)
    
    #confirmed means no workorders - push button_plan
    if r[0]['state'] in ['confirmed']:
        print("Creating workorders")
        r = call(url, "object", "execute", DB, uid, PASS, 'mrp.production', 'button_plan', mo)
        print('button_plan:', r)

        if r != True:
            print("Cannot create workorders")
            error_message('mrp.production', mo[0], 'Cannot create workorders')
            blink(2, 'r', 1)
            return


    #search workorder
    wo = call(url, "object", "execute", DB, uid, PASS, 'mrp.workorder', 'search',
                  [['production_id', '=', mo[0]], ['workcenter_id', '=', wc], ['state','not in',['done','cancel']]], 0, 1 )
    print('wo:', wo)

    if wo == []:
        print('Workorder Not found')
        #error_message('mrp.production', mo[0], 'Workorder Not found')
        #blink(1, 'r', 1)
        return

    #read wo obj
    r = call(url, "object", "execute", DB, uid, PASS, 'mrp.workorder', 'read',  wo, ['name', 'state'] )
    print('wo:', r)
                  
    if r[0]['state'] in ['pending', 'ready']:
        #call button_start method
        r = call(url, "object", "execute", DB, uid, PASS, 'mrp.workorder', 'button_start', wo)
        print('button_start:', r)
        if r == True:
            #call record_production method
            time.sleep(1)
            r = call(url, "object", "execute", DB, uid, PASS, 'mrp.workorder', 'record_production', wo)
            print('record_production:', r)
            if r == True:
                blink(1, 'g', 1)
                return
            else:
                print("Cannot finish workorder")
                error_message('mrp.production', mo[0], 'Cannot finish workorder')
                blink(2, 'r', 1)

        else:
            print("Cannot start workorder")
            error_message('mrp.production', mo[0], 'Cannot start workorder')
            blink(2, 'r', 1)
            return

    if r[0]['state'] in ['progress']:
        #call record_production method
        r = call(url, "object", "execute", DB, uid, PASS, 'mrp.workorder', 'record_production', wo)
        print('record_production:', r)
        if r == True:
            blink(1, 'g', 1)
            return
        else:
            print("Cannot finish workorder")
            error_message('mrp.production', mo[0], 'Cannot finish workorder')
            blink(2, 'r', 1)
            return

    return

#error message
def error_message(model, res_id, message):
    try:
        args={
            'subject': 'RPC error',
            'model': model,
            'res_id': res_id,
            'message_type': 'notification',
            #'needaction_partner_ids': notification_uids,
            #'partner_ids': notification_uids,
            'body': message,
            }
        r = call(url, "object", "execute", DB, uid, PASS, 'mail.message', 'create', args)
    except:
        print("Cannot send message to object")

#main flow
do_connect()

# log in the given database
url = "http://%s:%s/jsonrpc" % (HOST, PORT)
uid = call(url, "common", "login", DB, USER, PASS)

#perform reading
do_read()
