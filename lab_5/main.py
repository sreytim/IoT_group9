import network
import socket
from machine import Pin, I2C, PWM
import neopixel
import tcs34725
import time

# ─── WiFi ───────────────────────────────────────────
SSID     = "Robotic WIFI"
PASSWORD = "rbtWIFI@2025"

wifi = network.WLAN(network.STA_IF)
wifi.active(True)
wifi.connect(SSID, PASSWORD)
print("Connecting", end="")
while not wifi.isconnected():
    pass
print("\nConnected!")
print("ESP32 IP:", wifi.ifconfig()[0])

# ─── Sensor ─────────────────────────────────────────
i2c    = I2C(0, scl=Pin(22), sda=Pin(21))
sensor = tcs34725.TCS34725(i2c)

# ─── NeoPixel ───────────────────────────────────────
NUM_PIXELS = 24
np = neopixel.NeoPixel(Pin(23), NUM_PIXELS)

# ─── Motor ──────────────────────────────────────────
pwm = PWM(Pin(14), freq=1000)
IN1 = Pin(26, Pin.OUT)
IN2 = Pin(27, Pin.OUT)

# ─── State ──────────────────────────────────────────
rgb_r        = 0
rgb_g        = 0
rgb_b        = 0
last_color   = "UNKNOWN"
manual_neo   = False
motor_state  = "STOP"   # "FORWARD", "BACKWARD", "STOP"

# ─── Color Classification ───────────────────────────
def classify_color(r, g, b):
    if r < 800 and g < 800 and b < 800:
        return "UNKNOWN"
    if r > g and r > b:
        return "RED"
    elif g > r and g > b:
        return "GREEN"
    elif b > r and b > g:
        return "BLUE"
    else:
        return "UNKNOWN"

# ─── NeoPixel ───────────────────────────────────────
def set_neopixel_color(color):
    if color == "RED":
        rgb = (255, 0, 0)
    elif color == "GREEN":
        rgb = (0, 255, 0)
    elif color == "BLUE":
        rgb = (0, 0, 255)
    else:
        rgb = (255, 255, 255)
    for i in range(NUM_PIXELS):
        np[i] = rgb
    np.write()

def set_neopixel_rgb(r, g, b):
    for i in range(NUM_PIXELS):
        np[i] = (int(r), int(g), int(b))
    np.write()

# ─── Motor ──────────────────────────────────────────
def run_motor():
    global motor_state
    if motor_state == "FORWARD":
        IN1.value(1)
        IN2.value(0)
        pwm.duty(600)
    elif motor_state == "BACKWARD":
        IN1.value(0)
        IN2.value(1)
        pwm.duty(600)
    elif motor_state == "STOP":
        IN1.value(0)
        IN2.value(0)
        pwm.duty(0)

def set_motor_by_color(color):
    # Only run auto motor if manual motor is stopped
    if motor_state == "STOP":
        IN1.value(1)
        IN2.value(0)
        if color == "RED":
            pwm.duty(700)
        elif color == "GREEN":
            pwm.duty(500)
        elif color == "BLUE":
            pwm.duty(300)
        else:
            pwm.duty(0)

# ─── Helper ─────────────────────────────────────────
def extract_value(request):
    try:
        val = int(float(request.split("value=")[1].split(" ")[0].split("&")[0]))
        return max(0, min(255, val))
    except:
        return 0

# ─── Web Server ─────────────────────────────────────
server_addr = socket.getaddrinfo("0.0.0.0", 80)[0][-1]
server = socket.socket()
server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
server.bind(server_addr)
server.listen(5)
server.setblocking(False)
print("Server running...")
print()

# ─── Main Loop ──────────────────────────────────────
while True:

    # ── Keep motor running continuously ─────────────
    run_motor()

    # ── Auto sensor ─────────────────────────────────
    r, g, b, c = sensor.read_raw()
    color = classify_color(r, g, b)
    if color == "UNKNOWN":
        color = last_color
    else:
        last_color = color

    if not manual_neo:
        set_neopixel_color(color)

    if motor_state == "STOP":
        set_motor_by_color(color)

    print("R:", r, " G:", g, " B:", b,
          " --> Color:", color,
          " Motor:", motor_state,
          " Manual:", manual_neo)

    # ── Check MIT App Request ────────────────────────
    try:
        client, client_addr = server.accept()
        request = client.recv(1024).decode()

        if "GET /forward" in request:
            motor_state = "FORWARD"
            run_motor()
            print("Motor: FORWARD (continuous)")
            response = "Forward"

        elif "GET /backward" in request:
            motor_state = "BACKWARD"
            run_motor()
            print("Motor: BACKWARD (continuous)")
            response = "Backward"

        elif "GET /stop" in request:
            motor_state = "STOP"
            run_motor()
            print("Motor: STOP")
            response = "Stop"

        elif "GET /color" in request:
            response = "COLOR:" + last_color

        elif "GET /auto" in request:
            manual_neo = False
            response = "Auto mode"

        elif "GET /red" in request:
            rgb_r = extract_value(request)
            manual_neo = True
            set_neopixel_rgb(rgb_r, rgb_g, rgb_b)
            print("RGB:", rgb_r, rgb_g, rgb_b)
            response = "Red: " + str(rgb_r)

        elif "GET /green" in request:
            rgb_g = extract_value(request)
            manual_neo = True
            set_neopixel_rgb(rgb_r, rgb_g, rgb_b)
            print("RGB:", rgb_r, rgb_g, rgb_b)
            response = "Green: " + str(rgb_g)

        elif "GET /blue" in request:
            rgb_b = extract_value(request)
            manual_neo = True
            set_neopixel_rgb(rgb_r, rgb_g, rgb_b)
            print("RGB:", rgb_r, rgb_g, rgb_b)
            response = "Blue: " + str(rgb_b)

        else:
            response = "Invalid"

        client.send("HTTP/1.1 200 OK\r\nContent-Type: text/plain\r\n\r\n")
        client.send(response)
        client.close()

    except:
        pass

    time.sleep(0.3)