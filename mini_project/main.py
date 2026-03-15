# ==============================
# SMART IoT PARKING - ESP32 SIDE
# Hardware + Web Server only
# ==============================

import gc
import network
import uasyncio as asyncio
import utime
from machine import Pin, PWM, SoftI2C, time_pulse_us
import dht
from tm1637 import TM1637

try:
    from machine_i2c_lcd import I2cLcd
except:
    I2cLcd = None


# ------------------------------
# CONFIG
# ------------------------------
SSID = "Polyvivoath"
PASSWORD = "12915527"

ENABLE_WEB = True
WEB_PORT = 8080
WEB_KEY = "parking123"
DEBUG = False

DIST_OPEN_CM = 15
DIST_CLOSE_CM = 20
CLEAR_HOLD_MS = 3000
TEMP_LIGHT_THRESHOLD = 30

ULTRA_PERIOD_MS = 250
DHT_PERIOD_MS = 4000
LCD_PERIOD_MS = 1500
DISPLAY_PERIOD_MS = 1500
WIFI_RETRY_MS = 6000


# ------------------------------
# PINS
# ------------------------------
TRIG = Pin(5, Pin.OUT, value=0)
ECHO = Pin(18, Pin.IN)

IR1 = Pin(32, Pin.IN, Pin.PULL_UP)
IR2 = Pin(33, Pin.IN, Pin.PULL_UP)
IR3 = Pin(12, Pin.IN, Pin.PULL_UP)
IR4 = Pin(14, Pin.IN, Pin.PULL_UP)

LED = Pin(2, Pin.OUT, value=0)   # Built-in ESP32 LED
SERVO_PWM = PWM(Pin(25), freq=50)

DHT_SENSOR = dht.DHT11(Pin(4))
tm = TM1637(clk_pin=15, dio_pin=2, brightness=4)


# ------------------------------
# LCD
# ------------------------------
lcd = None
last_lcd_1 = ""
last_lcd_2 = ""

def init_lcd():
    global lcd
    if I2cLcd is None:
        print("[LCD] Library not found")
        return
    try:
        i2c = SoftI2C(sda=Pin(21), scl=Pin(22), freq=100000)
        utime.sleep_ms(250)
        devices = i2c.scan()
        print("[LCD] I2C devices:", [hex(d) for d in devices])
        addr = None
        if 0x27 in devices:
            addr = 0x27
        elif 0x3F in devices:
            addr = 0x3F
        if addr is None:
            print("[LCD] No LCD detected")
            return
        lcd = I2cLcd(i2c, addr, 2, 16)
        lcd.clear()
        lcd.putstr("LCD Ready")
        print("[LCD] Ready at", hex(addr))
    except Exception as e:
        print("[LCD] Init failed:", e)

def lcd_status(line1="", line2=""):
    global lcd, last_lcd_1, last_lcd_2
    if lcd is None:
        return
    line1 = str(line1)[:16]
    line2 = str(line2)[:16]
    if line1 == last_lcd_1 and line2 == last_lcd_2:
        return
    try:
        lcd.clear()
        lcd.putstr(line1)
        lcd.move_to(0, 1)
        lcd.putstr(line2)
        last_lcd_1 = line1
        last_lcd_2 = line2
    except Exception as e:
        print("[LCD] Error:", e)

init_lcd()


# ------------------------------
# STATE
# ------------------------------
state = {
    "wifi": False,
    "ip": None,
    "gate": "CLOSED",
    "slots": 0,
    "temp": None,
    "hum": None,
    "led": 0,
    "led_mode": "AUTO",
    "last_distance_cm": None,
    "last_distance_seen_ms": None,
    "wifi_ready_once": False,
}


# ------------------------------
# UTILS
# ------------------------------
def dprint(*a):
    if DEBUG:
        print(*a)

def clamp(v, lo, hi):
    if v < lo:
        return lo
    if v > hi:
        return hi
    return v


# ------------------------------
# HARDWARE HELPERS
# ------------------------------
def servo_angle_to_pulse_ns(angle):
    angle = clamp(angle, 0, 180)
    us = 500 + (2000 * angle) // 180
    return us * 1000

def servo_write_angle(angle):
    try:
        SERVO_PWM.duty_ns(servo_angle_to_pulse_ns(180 - angle))
    except:
        try:
            duty = int(26 + (102 * clamp(angle, 0, 180)) / 180)
            SERVO_PWM.duty(clamp(duty, 26, 128))
        except Exception as e:
            dprint("[SERVO] Error:", e)

def set_gate(open_):
    try:
        if open_ and state["gate"] != "OPEN":
            servo_write_angle(90)
            utime.sleep_ms(250)
            state["gate"] = "OPEN"
            print("[GATE] OPEN")
        elif (not open_) and state["gate"] != "CLOSED":
            servo_write_angle(0)
            utime.sleep_ms(250)
            state["gate"] = "CLOSED"
            print("[GATE] CLOSED")
    except Exception as e:
        print("[GATE] Error:", e)

def set_led(value):
    LED.value(value)
    state["led"] = value

def read_slots():
    s1 = 0 if IR1.value() == 0 else 1
    s2 = 0 if IR2.value() == 0 else 1
    s3 = 0 if IR3.value() == 0 else 1
    s4 = 0 if IR4.value() == 0 else 1
    return s1 + s2 + s3 + s4


# ------------------------------
# WIFI
# ------------------------------
async def wifi_manager():
    print("[WIFI] Task started")
    wlan = network.WLAN(network.STA_IF)
    wlan.active(True)

    while True:
        try:
            if not wlan.isconnected():
                state["wifi"] = False
                state["ip"] = None
                lcd_status("Connecting WiFi", "")
                try:
                    wlan.disconnect()
                except:
                    pass
                utime.sleep_ms(500)
                wlan.connect(SSID, PASSWORD)
                for _ in range(15):
                    if wlan.isconnected():
                        break
                    await asyncio.sleep_ms(1000)

            if wlan.isconnected():
                state["wifi"] = True
                ip = wlan.ifconfig()[0]
                if ip != state["ip"]:
                    state["ip"] = ip
                    state["wifi_ready_once"] = True
                    print("[WIFI] Connected:", ip)
                    lcd_status("WiFi Connected", ip)
            else:
                state["wifi"] = False
                state["ip"] = None

        except Exception as e:
            print("[WIFI] Error:", e)
            state["wifi"] = False
            state["ip"] = None

        await asyncio.sleep_ms(WIFI_RETRY_MS)


# ------------------------------
# ULTRASONIC
# ------------------------------
BUF_MAX = 3
dist_buf = []

def median(vals):
    if not vals:
        return None
    s = sorted(vals)
    return s[len(s) // 2]

def get_distance_cm(timeout_us=30000):
    try:
        TRIG.value(0)
        utime.sleep_us(5)
        TRIG.value(1)
        utime.sleep_us(10)
        TRIG.value(0)
        if ECHO.value() == 1:
            return None
        dur = time_pulse_us(ECHO, 1, timeout_us)
        if dur <= 0:
            return None
        return (dur * 0.0343) / 2
    except Exception as e:
        dprint("[ULTRA] Error:", e)
        return None


# ------------------------------
# WEB
# ------------------------------
def build_status_json():
    return (
        '{"slots":' + str(state["slots"]) +
        ',"temp":' + str(-1 if state["temp"] is None else state["temp"]) +
        ',"hum":' + str(-1 if state["hum"] is None else state["hum"]) +
        ',"gate":"' + state["gate"] + '"' +
        ',"led":' + str(state["led"]) +
        ',"led_mode":"' + state["led_mode"] + '"' +
        ',"dist":' + str(-1 if state["last_distance_cm"] is None else state["last_distance_cm"]) +
        '}'
    )

def build_dashboard_html():
    return (
        "<!DOCTYPE html><html><head>"
        "<meta charset=UTF-8>"
        "<meta name=viewport content='width=device-width,initial-scale=1'>"
        "<title>Smart Parking</title><style>"
        "body{font-family:Arial,sans-serif;margin:0;padding:16px;background:#e8eaf6;}"
        ".card{background:#fff;border-radius:16px;padding:20px;max-width:400px;"
        "margin:auto;box-shadow:0 4px 12px rgba(0,0,0,.1);text-align:center;}"
        "h2{margin:0 0 4px;color:#1a237e;font-size:20px;}"
        ".sub{color:#888;font-size:13px;margin-bottom:16px;}"
        ".grid{display:grid;grid-template-columns:1fr 1fr;gap:10px;margin-bottom:16px;}"
        ".box{background:#f5f5f5;border-radius:10px;padding:12px;}"
        ".full{grid-column:span 2;border-left:4px solid #5c6bc0;}"
        ".lbl{font-size:11px;color:#999;text-transform:uppercase;letter-spacing:1px;}"
        ".val{font-size:18px;font-weight:700;color:#1a237e;}"
        ".big{font-size:28px;font-weight:800;}"
        ".btns{display:grid;grid-template-columns:1fr 1fr;gap:8px;}"
        "button{display:block;width:100%;padding:13px;border-radius:10px;color:#fff;"
        "border:none;font-weight:600;font-size:14px;cursor:pointer;}"
        "button:active{opacity:.8;}"
        ".go{background:#388e3c;}.gc{background:#c62828;}"
        ".lo{background:#1565c0;}.lf{background:#455a64;}"
        ".la{background:#6a1b9a;}"
        ".msg{margin-top:10px;font-size:13px;color:#555;min-height:18px;}"
        "</style></head><body><div class=card>"
        "<h2>Smart Parking</h2>"
        "<div class=sub id=ip></div>"
        "<div class=grid>"
        "<div class='box full'><div class=lbl>Available Slots</div>"
        "<div class='val big' id=slots>--</div></div>"
        "<div class=box><div class=lbl>Temp</div><div class=val id=temp>--</div></div>"
        "<div class=box><div class=lbl>Humidity</div><div class=val id=hum>--</div></div>"
        "<div class=box><div class=lbl>Gate</div><div class=val id=gate>--</div></div>"
        "<div class=box><div class=lbl id=ledlbl>LED</div><div class=val id=led>--</div></div>"
        "</div><div class=btns>"
        "<button class=go onclick=\"cmd('/open')\">OPEN GATE</button>"
        "<button class=gc onclick=\"cmd('/close')\">CLOSE GATE</button>"
        "<button class=lo onclick=\"cmd('/led_on')\">LED ON</button>"
        "<button class=lf onclick=\"cmd('/led_off')\">LED OFF</button>"
        "<button class=la style='grid-column:span 2' onclick=\"cmd('/led_auto')\">LED AUTO</button>"
        "</div>"
        "<div class=msg id=msg></div>"
        "</div><script>"
        "var K='" + WEB_KEY + "';"
        "function show(d){"
        "document.getElementById('slots').textContent=d.slots+' / 4';"
        "document.getElementById('slots').style.color=d.slots>0?'#2a2':'#c00';"
        "document.getElementById('temp').textContent=(d.temp==-1?'--':d.temp)+'\\u00b0C';"
        "document.getElementById('hum').textContent=(d.hum==-1?'--':d.hum)+'%';"
        "document.getElementById('gate').textContent=d.gate;"
        "document.getElementById('led').textContent=d.led?'ON':'OFF';"
        "document.getElementById('led').style.color=d.led?'#2a2':'#aaa';"
        "document.getElementById('ledlbl').textContent='LED ('+d.led_mode+')';"
        "document.getElementById('ip').textContent=window.location.host;"
        "}"
        "function update(){"
        "fetch('/status').then(function(r){return r.json();}).then(show)"
        ".catch(function(){document.getElementById('msg').textContent='Connection lost...';});}"
        "function cmd(path){"
        "fetch(path+'?key='+K)"
        ".then(function(){document.getElementById('msg').textContent='Done!';setTimeout(function(){document.getElementById('msg').textContent='';},1500);update();})"
        ".catch(function(){document.getElementById('msg').textContent='Failed';});}"
        "update();"
        "setInterval(update,5000);"
        "</script></body></html>"
    )

async def send_response(writer, body, content_type="text/html"):
    try:
        if isinstance(body, str):
            body_bytes = body.encode()
        else:
            body_bytes = body
        header = (
            "HTTP/1.1 200 OK\r\n"
            "Content-Type: " + content_type + "\r\n"
            "Content-Length: " + str(len(body_bytes)) + "\r\n"
            "Access-Control-Allow-Origin: *\r\n"
            "Connection: close\r\n\r\n"
        )
        await writer.awrite(header)
        await writer.awrite(body_bytes)
    finally:
        try:
            await writer.aclose()
        except:
            try:
                writer.close()
            except:
                pass

async def handle_http(reader, writer):
    try:
        req = await reader.read(512)
        if not req:
            try:
                await writer.aclose()
            except:
                pass
            return
        req_str = req.decode("utf-8", "ignore")
        if not req_str.strip():
            try:
                await writer.aclose()
            except:
                pass
            return

        first = req_str.split("\r\n", 1)[0]
        parts = first.split()
        path = "/"
        if len(parts) >= 2:
            path = parts[1]

        if path == "/ping":
            await send_response(writer, "ESP32 OK", "text/plain")
            return

        if path == "/status":
            await send_response(writer, build_status_json(), "application/json")
            return

        if path == "/open?key=" + WEB_KEY:
            set_gate(True)
            await send_response(writer, "OK", "text/plain")
            return

        if path == "/close?key=" + WEB_KEY:
            set_gate(False)
            await send_response(writer, "OK", "text/plain")
            return

        if path == "/led_on?key=" + WEB_KEY:
            state["led_mode"] = "MANUAL"  # lock out AUTO loop
            set_led(1)                     # turn ON immediately
            print("[LED] Manual ON")
            await send_response(writer, "OK", "text/plain")
            return

        if path == "/led_off?key=" + WEB_KEY:
            state["led_mode"] = "MANUAL"  # lock out AUTO loop
            set_led(0)                     # turn OFF immediately
            print("[LED] Manual OFF")
            await send_response(writer, "OK", "text/plain")
            return

        if path == "/led_auto?key=" + WEB_KEY:
            state["led_mode"] = "AUTO"    # hand back to temp loop
            print("[LED] Auto mode")
            await send_response(writer, "OK", "text/plain")
            return

        await send_response(writer, build_dashboard_html(), "text/html")

    except Exception as e:
        dprint("[HTTP ERROR]", e)
        try:
            await send_response(writer, "500 Error", "text/plain")
        except:
            try:
                writer.close()
            except:
                pass

async def web_server():
    print("[WEB] Task started")
    started = False
    while True:
        try:
            if ENABLE_WEB and state["wifi"] and state["ip"] and not started:
                print("[WEB] Starting HTTP server on port", WEB_PORT)
                await asyncio.start_server(handle_http, "0.0.0.0", WEB_PORT)
                print("[HTTP] Listening on", WEB_PORT)
                print("Web Dashboard: http://{}:{}".format(state["ip"], WEB_PORT))
                started = True
            await asyncio.sleep_ms(3000)
        except Exception as e:
            print("[WEB] Failed:", e)
            started = False
            await asyncio.sleep_ms(5000)


# ------------------------------
# TASKS
# ------------------------------
async def task_sensors():
    print("[SENSORS] Task started")
    last_lcd_ms = utime.ticks_ms()
    last_dht_ms = utime.ticks_ms()

    while True:
        try:
            state["slots"] = read_slots()
            now = utime.ticks_ms()

            d = get_distance_cm()
            if d is not None and 2 <= d <= 150:
                dist_buf.append(d)
                if len(dist_buf) > BUF_MAX:
                    dist_buf.pop(0)
                state["last_distance_cm"] = round(median(dist_buf), 1)
                state["last_distance_seen_ms"] = now
            else:
                if state["last_distance_seen_ms"] is not None:
                    if utime.ticks_diff(now, state["last_distance_seen_ms"]) > 1500:
                        state["last_distance_cm"] = None

            if utime.ticks_diff(now, last_dht_ms) >= DHT_PERIOD_MS:
                try:
                    DHT_SENSOR.measure()
                    state["temp"] = DHT_SENSOR.temperature()
                    state["hum"] = DHT_SENSOR.humidity()
                except Exception as e:
                    dprint("[DHT] Error:", e)
                last_dht_ms = now

            # AUTO mode only — MANUAL mode is never touched here
            if state["led_mode"] == "AUTO":
                t = state["temp"]
                if t is not None:
                    if t > TEMP_LIGHT_THRESHOLD and state["led"] == 0:
                        set_led(1)   # turn ON when temp rises above threshold
                    elif t < (TEMP_LIGHT_THRESHOLD - 1) and state["led"] == 1:
                        set_led(0)   # turn OFF when temp drops below 29C

            if utime.ticks_diff(now, last_lcd_ms) >= LCD_PERIOD_MS:
                lcd_status(
                    "Slots:{} {}".format(state["slots"], state["gate"]),
                    "{}C {}% LED:{}".format(
                        "-" if state["temp"] is None else state["temp"],
                        "-" if state["hum"] is None else state["hum"],
                        "ON" if state["led"] else "OF"
                    )
                )
                last_lcd_ms = now

        except Exception as e:
            dprint("[SENSOR LOOP ERROR]", e)

        await asyncio.sleep_ms(ULTRA_PERIOD_MS)

async def task_gate_automation():
    print("[AUTO GATE] Task started")
    near_count = 0
    far_count = 0
    opened_ms = None

    while True:
        try:
            dist = state["last_distance_cm"]
            slots = state["slots"]
            now = utime.ticks_ms()

            if dist is None:
                near_count = 0
                far_count = 0
                await asyncio.sleep_ms(150)
                continue

            if dist < DIST_OPEN_CM and slots > 0:
                near_count += 1
            else:
                near_count = 0

            if near_count >= 3 and state["gate"] != "OPEN":
                set_gate(True)
                opened_ms = now
                far_count = 0

            if state["gate"] == "OPEN":
                if dist > DIST_CLOSE_CM:
                    far_count += 1
                else:
                    far_count = 0
                if opened_ms is not None:
                    if utime.ticks_diff(now, opened_ms) >= CLEAR_HOLD_MS and far_count >= 3:
                        set_gate(False)
                        opened_ms = None
                        near_count = 0
                        far_count = 0

        except Exception as e:
            dprint("[AUTO GATE ERROR]", e)

        await asyncio.sleep_ms(150)

async def task_tm1637_display():
    print("[7SEG] Task started")
    while True:
        try:
            tm.show_digit(int(state["slots"]))
        except:
            pass
        await asyncio.sleep_ms(DISPLAY_PERIOD_MS)


# ------------------------------
# MAIN
# ------------------------------
async def main():
    set_gate(False)
    set_led(0)
    lcd_status("System Start", "Please wait")

    asyncio.create_task(wifi_manager())
    asyncio.create_task(task_sensors())
    asyncio.create_task(task_gate_automation())
    asyncio.create_task(task_tm1637_display())

    if ENABLE_WEB:
        asyncio.create_task(web_server())

    while True:
        gc.collect()
        await asyncio.sleep_ms(1500)

try:
    asyncio.run(main())
finally:
    asyncio.new_event_loop()