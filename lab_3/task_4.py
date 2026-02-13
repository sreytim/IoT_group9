from machine import Pin
from tm1637 import TM1637
import time
import network
import urequests

# ---------- BLYNK CONFIG ----------
BLYNK_TOKEN = "cAeyF8Z0r_AxKmFNvyX3A3zVxesJK7O-"
BLYNK_URL   = "http://blynk.cloud/external/api"

# ---------- WIFI CONFIG ----------
WIFI_SSID = "Robotic WIFI"
WIFI_PASS = "rbtWIFI@2025"

# ---------- HARDWARE ----------
tm = TM1637(
    clk_pin=17,
    dio_pin=16,
    brightness=5
)

ir_sensor = Pin(12, Pin.IN)

# ---------- WIFI CONNECTION ----------
wlan = network.WLAN(network.STA_IF)
wlan.active(True)
wlan.connect(WIFI_SSID, WIFI_PASS)

print("Connecting to WiFi...")
while not wlan.isconnected():
    time.sleep(0.5)

print("WiFi connected")
print("System Ready")

# ---------- COUNTER ----------
count = 0
tm.show_number(count)

# ---------- MAIN LOOP ----------
while True:
    if ir_sensor.value() == 0:   # Object detected
        count += 1
        print("Count:", count)

        # Update TM1637 using show_count()
        tm.show_number(count)

        # Send value to Blynk 
        try:
            urequests.get(
                f"{BLYNK_URL}/update?token={BLYNK_TOKEN}&V7={count}"
            ).close()
        except:
            print("Blynk update failed")

        # Debounce delay
        time.sleep(0.8)

    time.sleep(0.1)
