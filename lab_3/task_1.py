from machine import Pin
import time
import network
import urequests as requests

# ---------- WIFI ----------
WIFI_SSID = "Robotic WIFI"
WIFI_PASS = "rbtWIFI@2025"

# ---------- BLYNK ----------
BLYNK_TOKEN = "cAeyF8Z0r_AxKmFNvyX3A3zVxesJK7O-"
BLYNK_API   = "http://blynk.cloud/external/api"

# ---------- IR SENSOR ----------
ir = Pin(12, Pin.IN)

# ---------- WIFI CONNECT ----------
wifi = network.WLAN(network.STA_IF)
wifi.active(True)
wifi.connect(WIFI_SSID, WIFI_PASS)

print("Connecting to WiFi...")
while not wifi.isconnected():
    time.sleep(1)
print("WiFi connected!")

# ---------- SEND TEXT TO BLYNK LABEL ----------
def send_to_blynk_label(message):
    try:
        # Encode spaces as %20 for URL safety
        message = message.replace(" ", "%20")
        url = f"{BLYNK_API}/update?token={BLYNK_TOKEN}&V4={message}"
        r = requests.get(url)
        r.close()
    except Exception as e:
        print("Blynk error:", e)

# ---------- MAIN LOOP ----------
while True:
    value = ir.value()  # 0 = obstacle, 1 = no obstacle

    if value == 0:
        status_text = "Detected"
        print(status_text)
    else:
        status_text = "Not Detected"
        print(status_text)

    send_to_blynk_label(status_text)
    time.sleep(0.5)
