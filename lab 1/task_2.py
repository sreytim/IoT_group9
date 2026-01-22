import network
import urequests
import time

# ---------- WIFI ----------
SSID = "Robotic WIFI"
PASSWORD = "rbtWIFI@2025"

# ---------- TELEGRAM ----------
BOT_TOKEN = "8576769772:AAFr_VC-E2PKXk1Ec5fwyiqG21qeK0uf--I"
CHAT_ID = "-5055627751"

URL_SEND = "https://api.telegram.org/bot{}/sendMessage".format(BOT_TOKEN)
URL_UPDATES = "https://api.telegram.org/bot{}/getUpdates".format(BOT_TOKEN)
last_update_id = 0

# ---------- CONNECT WIFI ----------
wifi = network.WLAN(network.STA_IF)
wifi.active(True)
wifi.connect(SSID, PASSWORD)

print("Connecting to WiFi...")
while not wifi.isconnected():
    time.sleep(1)

print("WiFi connected")

# ---------- SEND MESSAGE ----------
def send_message(text):
    try:
        r = urequests.post(URL_SEND, json={
            "chat_id": CHAT_ID,
            "text": text
        })
        r.close()
    except Exception as e:
        print("Telegram send error:", e)

# ---------- READ TELEGRAM MESSAGE ----------
def check_command():
    global last_update_id
    try:
        r = urequests.get(
            URL_UPDATES + "?offset={}".format(last_update_id + 1)
        )
        data = r.json()
        r.close()

        if data["ok"]:
            for update in data["result"]:
                last_update_id = update["update_id"]

                if "message" in update:
                    text = update["message"].get("text", "")
                    chat_id = update["message"]["chat"]["id"]
                    return text

    except Exception as e:
        print("Telegram read error:", e)

    return None

# ---------- START ----------
send_message("✅ ESP32 is online and listening.")

# ---------- MAIN LOOP ----------
while True:
    cmd = check_command()

    if cmd:
        print("Received:", cmd)
        send_message("📩 You sent: " + cmd)

    time.sleep(2)