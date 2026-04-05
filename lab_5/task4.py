from machine import Pin, I2C, PWM
import time
import tcs34725
import neopixel

# Setup
i2c = I2C(0, scl=Pin(22), sda=Pin(21))
sensor = tcs34725.TCS34725(i2c)
NUM_PIXELS = 24
np = neopixel.NeoPixel(Pin(23), NUM_PIXELS)

# Motor Setup
pwm = PWM(Pin(14), freq=1000)
IN1 = Pin(26, Pin.OUT)
IN2 = Pin(27, Pin.OUT)

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

def set_neopixel(color):
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

def set_motor(color):
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

print("=== Task 4: Motor PWM Control ===")
print("Place colored object in front of sensor...")
print()

last_color = "UNKNOWN"

while True:
    r, g, b, c = sensor.read_raw()
    color = classify_color(r, g, b)

    if color == "UNKNOWN":
        color = last_color
    else:
        last_color = color

    set_neopixel(color)
    set_motor(color)
    print("R:", r, " G:", g, " B:", b, " --> Detected:", color, "--> PWM:", 700 if color=="RED" else 500 if color=="GREEN" else 300)
    time.sleep(1)