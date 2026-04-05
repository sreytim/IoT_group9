from machine import Pin, I2C
import time
import tcs34725

i2c = I2C(0, scl=Pin(22), sda=Pin(21))
sensor = tcs34725.TCS34725(i2c)

def classify_color(r, g, b):
    if r > g and r > b:
        return "RED"
    elif g > r and g > b:
        return "GREEN"
    elif b > r and b > g:
        return "BLUE"
    else:
        return "UNKNOWN"

print("=== Task 2: Color Classification ===")
print("Place colored object in front of sensor...")
print()

while True:
    r, g, b, c = sensor.read_raw()
    color = classify_color(r, g, b)
    print("R:", r, " G:", g, " B:", b, " --> Detected:", color)
    time.sleep(1)