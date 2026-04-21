import machine
from machine import Pin, SPI
import mfrc522
import sdcard
import os
import time
import urequests
import json
import network

# --- CONFIGURATION ---
WIFI_SSID = "Zenk1k0"
WIFI_PASS = "092567088 "
PROJECT_ID = "lab6-f76c3"
API_KEY = "AIzaSyDiyRkLoMC_xr2LTTYaULTG6ou85FQdeWo"
COLLECTION = "attendance"
ALLOWED_UIDS = ["1151181145114", "12913712822158"]

# --- HARDWARE SETUP ---
# 1. PRE-INITIALIZATION: Set CS pins HIGH immediately (prevents bus interference)
cs_rfid = Pin(16, Pin.OUT)
cs_sd = Pin(13, Pin.OUT)
cs_rfid.value(1)
cs_sd.value(1)

# 2. RFID INIT (SPI 1)
spi_rfid = SPI(1, baudrate=1000000, polarity=0, phase=0, sck=Pin(18), mosi=Pin(23), miso=Pin(19))
rdr = mfrc522.MFRC522(spi=spi_rfid, gpioRst=Pin(22), gpioCs=cs_rfid)

# 3. SD CARD INIT (SPI 2) - Using Pin 27 for MISO
spi_sd = SPI(2, baudrate=100000, sck=Pin(14), mosi=Pin(15), miso=Pin(27))
sd = sdcard.SDCard(spi_sd, cs_sd)

buzzer = Pin(4, Pin.OUT)

# --- FUNCTIONS ---
def connect_wifi():
    wlan = network.WLAN(network.STA_IF)
    wlan.active(True)
    wlan.connect(WIFI_SSID, WIFI_PASS)
    while not wlan.isconnected():
        time.sleep(1)
    print("Connected to WiFi")

def send_to_firestore(uid, name, sid, major, timestamp):
    url = f"https://firestore.googleapis.com/v1/projects/{PROJECT_ID}/databases/(default)/documents/{COLLECTION}?key={API_KEY}"
    payload = {
        "fields": {
            "uid": {"stringValue": uid},
            "name": {"stringValue": name},
            "studentID": {"stringValue": sid},
            "major": {"stringValue": major},
            "dateTime": {"stringValue": timestamp}
        }
    }
    try:
        response = urequests.post(url, json=payload)
        response.close()
    except Exception as e:
        print("Network Error:", e)

def save_to_sd(data):
    try:
        os.mount(sd, '/sd')
        with open('/sd/attendance.csv', 'a') as f:
            f.write(data + '\n')
        os.umount('/sd')
    except Exception as e:
        print("SD Error:", e)

def sync_sd_to_firestore():
    try:
        os.mount(sd, '/sd')
        with open('/sd/attendance.csv', 'r') as f:
            lines = f.readlines()
            for line in lines:
                # Assuming your CSV format is: card_id,name,sid,major,ts
                data = line.strip().split(',')
                if len(data) == 5:
                    send_to_firestore(data[0], data[1], data[2], data[3], data[4])
                    time.sleep(1) # Don't spam Firestore
        
        # Optional: Clear the file after uploading
        # with open('/sd/attendance.csv', 'w') as f:
        #     f.write("") 
        
        os.umount('/sd')
        print("Sync complete.")
    except Exception as e:
        print("Sync failed:", e)
        
# --- MAIN EXECUTION ---
connect_wifi()
print("Scan RFID...")

while True:
    (stat, tag_type) = rdr.request(rdr.REQIDL)
    if stat == rdr.OK:
        (stat, uid) = rdr.anticoll()
        if stat == rdr.OK:
            card_id = "".join([str(i) for i in uid])
            print("Scanned UID:", card_id)
            
            # --- VALIDATION LOGIC ---
            if card_id in ALLOWED_UIDS:
                # SUCCESS: Valid Student
                print("Access Granted")
                buzzer.value(1); time.sleep(0.3); buzzer.value(0) # Short beep
                
                ts = "2026-04-20 13:49:00" # Remember to use NTP for real-time
                save_to_sd(f"{card_id},Authorized Student,12345,CS,{ts}")
                send_to_firestore(card_id, "Authorized Student", "12345", "CS", ts)
            
            else:
                # INVALID: Unauthorized/Unknown Card
                print("Access Denied: Invalid UID")
                # Feedback: 3 quick beeps for error
                buzzer.value(1); time.sleep(3); buzzer.value(0);
                    
            time.sleep(2)