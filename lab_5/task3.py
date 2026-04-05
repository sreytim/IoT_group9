from machine import Pin, I2C
import time
import tcs34725
import neopixel

# Setup
i2c = I2C(0, scl=Pin(22), sda=Pin(21))
sensor = tcs34725.TCS34725(i2c)
NUM_PIXELS = 24
np = neopixel.NeoPixel(Pin(23), NUM_PIXELS)

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
        rgb = (255, 255, 255)  # WHITE when unknown
    for i in range(NUM_PIXELS):
        np[i] = rgb
    np.write()

print("=== Task 3: NeoPixel Control ===")
print("Place colored object in front of sensor...")
print()

last_color = "UNKNOWN"

while True:
    r, g, b, c = sensor.read_raw()
    color = classify_color(r, g, b)

    # If unknown, keep last known color
    if color == "UNKNOWN":
        color = last_color
    else:
        last_color = color

    set_neopixel(color)
    print("R:", r, " G:", g, " B:", b, " --> Detected:", color)
    time.sleep(1)