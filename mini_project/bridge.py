import time
import threading
import requests
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes


# =========================
# CONFIG
# =========================
ESP32_BASE = "http://192.168.1.182:8080"
WEB_KEY = "parking123"

TELEGRAM_BOT_TOKEN = "8571902485:AAGl3vs7oroGB3ACD7vouW9D0xBTcPrgIRM"
CHAT_ID = -1184577187

BLYNK_AUTH_TOKEN = "cAeyF8Z0r_AxKmFNvyX3A3zVxesJK7O-"
BLYNK_SERVER = "https://sgp1.blynk.cloud"
BLYNK_VPIN_GATE = "v0"
BLYNK_VPIN_TEMP = "v1"
BLYNK_VPIN_SLOTS = "v4"
BLYNK_VPIN_LED = "v5"
ENABLE_BLYNK = True


# =========================
# TELEGRAM HELPERS
# =========================
def allowed_chat(update: Update) -> bool:
    return True


def send_telegram_message(text: str):
    try:
        url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
        requests.post(url, data={"chat_id": CHAT_ID, "text": text}, timeout=5)
    except Exception as e:
        print("[TELEGRAM SEND ERROR]", e)


# =========================
# ESP32 HELPERS
# =========================
def esp32_get_status():
    try:
        r = requests.get(f"{ESP32_BASE}/status", timeout=5)
        r.raise_for_status()
        data = r.json()
        # Normalize -1 sentinel values back to None
        for key in ("temp", "hum", "dist"):
            if data.get(key) == -1:
                data[key] = None
        return data
    except Exception as e:
        print("[ESP32 STATUS ERROR]", e)
        return None


def esp32_open_gate():
    try:
        r = requests.get(f"{ESP32_BASE}/open?key={WEB_KEY}", timeout=5)
        return r.status_code in (200, 303)
    except Exception as e:
        print("[OPEN ERROR]", e)
        return False


def esp32_close_gate():
    try:
        r = requests.get(f"{ESP32_BASE}/close?key={WEB_KEY}", timeout=5)
        return r.status_code in (200, 303)
    except Exception as e:
        print("[CLOSE ERROR]", e)
        return False


def esp32_led_on():
    try:
        r = requests.get(f"{ESP32_BASE}/led_on?key={WEB_KEY}", timeout=5)
        return r.status_code in (200, 303)
    except Exception as e:
        print("[LED ON ERROR]", e)
        return False


def esp32_led_off():
    try:
        r = requests.get(f"{ESP32_BASE}/led_off?key={WEB_KEY}", timeout=5)
        return r.status_code in (200, 303)
    except Exception as e:
        print("[LED OFF ERROR]", e)
        return False


def esp32_led_auto():
    try:
        r = requests.get(f"{ESP32_BASE}/led_auto?key={WEB_KEY}", timeout=5)
        return r.status_code in (200, 303)
    except Exception as e:
        print("[LED AUTO ERROR]", e)
        return False


# =========================
# BLYNK HELPERS
# =========================
def blynk_update(pin, value):
    try:
        url = f"{BLYNK_SERVER}/external/api/update?token={BLYNK_AUTH_TOKEN}&{pin}={value}"
        r = requests.get(url, timeout=5)
        return r.status_code == 200
    except Exception as e:
        print("[BLYNK UPDATE ERROR]", e)
        return False


def blynk_get(pin):
    try:
        url = f"{BLYNK_SERVER}/external/api/get?token={BLYNK_AUTH_TOKEN}&{pin}"
        r = requests.get(url, timeout=5)
        if r.status_code == 200:
            return r.text.strip()
        return None
    except Exception as e:
        print("[BLYNK GET ERROR]", e)
        return None


# =========================
# TELEGRAM COMMANDS
# =========================
async def start_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    print("START command received:", update.effective_chat.id)
    if not allowed_chat(update):
        await update.message.reply_text("Unauthorized chat")
        return
    await update.message.reply_text(
        "Smart Parking Commands:\n"
        "/status    - Full system status\n"
        "/slots     - Available slots\n"
        "/temp      - Temperature & humidity\n"
        "/open      - Open gate\n"
        "/close     - Close gate\n"
        "/led_on    - Turn LED on (manual)\n"
        "/led_off   - Turn LED off (manual)\n"
        "/led_auto  - LED auto mode (temp-based)"
    )


async def status_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    print("STATUS command received:", update.effective_chat.id)
    if not allowed_chat(update):
        await update.message.reply_text("Unauthorized chat")
        return
    status = esp32_get_status()
    if not status:
        await update.message.reply_text("ESP32 not reachable")
        return
    temp = status.get("temp", "N/A")
    hum  = status.get("hum",  "N/A")
    dist = status.get("dist", "N/A")
    led_val  = "ON" if status.get("led", 0) else "OFF"
    led_mode = status.get("led_mode", "?")
    await update.message.reply_text(
        f"Slots : {status['slots']}\n"
        f"Temp  : {temp} C\n"
        f"Hum   : {hum} %\n"
        f"Gate  : {status['gate']}\n"
        f"LED   : {led_val} ({led_mode})\n"
        # f"Dist  : {dist} cm"
    )


async def slots_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    print("SLOTS command received:", update.effective_chat.id)
    if not allowed_chat(update):
        await update.message.reply_text("Unauthorized chat")
        return
    status = esp32_get_status()
    if not status:
        await update.message.reply_text("ESP32 not reachable")
        return
    await update.message.reply_text(f"Available slots: {status['slots']} / 4")


async def temp_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    print("TEMP command received:", update.effective_chat.id)
    if not allowed_chat(update):
        await update.message.reply_text("Unauthorized chat")
        return
    status = esp32_get_status()
    if not status:
        await update.message.reply_text("ESP32 not reachable")
        return
    temp = status.get("temp", "N/A")
    hum  = status.get("hum",  "N/A")
    await update.message.reply_text(
        f"Temperature : {temp} C\n"
        f"Humidity    : {hum} %"
    )


async def open_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    print("OPEN command received:", update.effective_chat.id)
    if not allowed_chat(update):
        await update.message.reply_text("Unauthorized chat")
        return
    ok = esp32_open_gate()
    await update.message.reply_text("Gate opened" if ok else "Failed to open gate")


async def close_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    print("CLOSE command received:", update.effective_chat.id)
    if not allowed_chat(update):
        await update.message.reply_text("Unauthorized chat")
        return
    ok = esp32_close_gate()
    await update.message.reply_text("Gate closed" if ok else "Failed to close gate")


async def led_on_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    print("LED_ON command received:", update.effective_chat.id)
    if not allowed_chat(update):
        await update.message.reply_text("Unauthorized chat")
        return
    ok = esp32_led_on()
    await update.message.reply_text("LED ON (manual)" if ok else "Failed")


async def led_off_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    print("LED_OFF command received:", update.effective_chat.id)
    if not allowed_chat(update):
        await update.message.reply_text("Unauthorized chat")
        return
    ok = esp32_led_off()
    await update.message.reply_text("LED OFF (manual)" if ok else "Failed")


async def led_auto_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    print("LED_AUTO command received:", update.effective_chat.id)
    if not allowed_chat(update):
        await update.message.reply_text("Unauthorized chat")
        return
    ok = esp32_led_auto()
    await update.message.reply_text("LED set to AUTO (temp-based)" if ok else "Failed")


# =========================
# BLYNK BACKGROUND LOOP
# =========================
def blynk_loop():
    last_temp = None
    last_slots = None
    last_gate = None
    last_led = None
    last_gate_cmd = None

    while True:
        try:
            status = esp32_get_status()

            if status and ENABLE_BLYNK:
                temp  = status.get("temp")
                slots = status.get("slots")
                gate  = 1 if status.get("gate") == "OPEN" else 0
                led   = status.get("led", 0)

                if temp is not None and temp != last_temp:
                    blynk_update(BLYNK_VPIN_TEMP, temp)
                    last_temp = temp

                if slots != last_slots:
                    blynk_update(BLYNK_VPIN_SLOTS, slots)
                    last_slots = slots

                if gate != last_gate:
                    blynk_update(BLYNK_VPIN_GATE, gate)
                    last_gate = gate

                if led != last_led:
                    blynk_update(BLYNK_VPIN_LED, led)
                    last_led = led

                cmd = blynk_get(BLYNK_VPIN_GATE)
                if cmd is not None and cmd != last_gate_cmd:
                    last_gate_cmd = cmd
                    if cmd == "1":
                        esp32_open_gate()
                    elif cmd == "0":
                        esp32_close_gate()

        except Exception as e:
            print("[BLYNK LOOP ERROR]", e)

        time.sleep(5)


# =========================
# MAIN
# =========================
def main():
    if ENABLE_BLYNK:
        t = threading.Thread(target=blynk_loop, daemon=True)
        t.start()

    app = ApplicationBuilder().token(TELEGRAM_BOT_TOKEN).build()

    app.add_handler(CommandHandler("start",    start_cmd))
    app.add_handler(CommandHandler("status",   status_cmd))
    app.add_handler(CommandHandler("slots",    slots_cmd))
    app.add_handler(CommandHandler("temp",     temp_cmd))
    app.add_handler(CommandHandler("open",     open_cmd))
    app.add_handler(CommandHandler("close",    close_cmd))
    app.add_handler(CommandHandler("led_on",   led_on_cmd))
    app.add_handler(CommandHandler("led_off",  led_off_cmd))
    app.add_handler(CommandHandler("led_auto", led_auto_cmd))

    print("Laptop bridge running...")

    while True:
        try:
            app.run_polling()
            break
        except Exception as e:
            print("[TELEGRAM POLLING ERROR]", e)
            time.sleep(5)


if __name__ == "__main__":
    main()