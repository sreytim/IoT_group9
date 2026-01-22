import network
import urequests
import time
from machine import Pin
import dht

# ---------- WIFI ----------
SSID = "Robotic WIFI"
PASSWORD = "rbtWIFI@2025"

# ---------- TELEGRAM ----------
BOT_TOKEN = "8576769772:AAFr_VC-E2PKXk1Ec5fwyiqG21qeK0uf--I"
CHAT_ID = "-5055627751"

URL_SEND = "https://api.telegram.org/bot{}/sendMessage".format(BOT_TOKEN)
URL_UPDATES = "https://api.telegram.org/bot{}/getUpdates".format(BOT_TOKEN)

# ---------- SENSOR & RELAY ----------
sensor = dht.DHT11(Pin(33))   # REQUIRED by lab
relay = Pin(15, Pin.OUT)
relay.off()

# ---------- SYSTEM STATE ----------
TEMP_THRESHOLD = 30
relay_state = False
last_update_id = 0
auto_off_sent = False

# ---------- WIFI CONNECT ----------
wifi = network.WLAN(network.STA_IF)
wifi.active(True)

def connect_wifi():
    if not wifi.isconnected():
        print("Connecting to WiFi...")
        wifi.connect(SSID, PASSWORD)
        timeout = 15
        while not wifi.isconnected() and timeout > 0:
            time.sleep(1)
            timeout -= 1

    if wifi.isconnected():
        print("WiFi connected:", wifi.ifconfig())
    else:
        print("WiFi failed")

connect_wifi()

# ---------- TELEGRAM FUNCTIONS ----------
def send_message(text):
    try:
        r = urequests.post(URL_SEND, json={
            "chat_id": CHAT_ID,
            "text": text
        })
        print("Telegram status:", r.status_code)
        r.close()
    except Exception as e:
        print("Telegram error:", e)

def check_command():
    global last_update_id
    try:
        r = urequests.get(URL_UPDATES + "?offset={}".format(last_update_id + 1))
        data = r.json()
        r.close()

        if data["ok"]:
            for update in data["result"]:
                last_update_id = update["update_id"]
                if "message" in update:
                    return update["message"]["text"]
    except Exception as e:
        print("Command error:", e)
    return None

# ---------- MAIN LOOP ----------
while True:

    # Auto WiFi reconnect
    if not wifi.isconnected():
        connect_wifi()
        time.sleep(2)
        continue

    # Read sensor safely
    try:
        sensor.measure()
        temp = sensor.temperature()
        hum = sensor.humidity()
        print("Temp:", temp, "Humidity:", hum)
    except OSError as e:
        print("DHT error:", e)
        time.sleep(5)
        continue

    # Telegram commands
    cmd = check_command()
    if cmd:
        print("Command:", cmd)

        if cmd == "/status":
            state = "ON" if relay_state else "OFF"
            send_message(
                "Temperature: {} °C\nHumidity: {} %\nRelay: {}".format(
                    temp, hum, state
                )
            )

        elif cmd == "/on":
            relay.on()
            relay_state = True
            send_message("Relay turned ON")

        elif cmd == "/off":
            relay.off()
            relay_state = False
            send_message("Relay turned OFF")

    # ---------- TEMPERATURE LOGIC ----------
    if temp >= TEMP_THRESHOLD:
        auto_off_sent = False
        if not relay_state:
            send_message("⚠️ ALERT! Temperature {} °C".format(temp))
    else:
        if relay_state:
            relay.off()
            relay_state = False
            if not auto_off_sent:
                send_message("ℹ️ Temperature normal. Relay auto-OFF")
                auto_off_sent = True

    time.sleep(5)   # REQUIRED: every 5 seconds
