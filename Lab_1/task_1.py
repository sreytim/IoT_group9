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

# ---------- SENSOR & RELAY ----------
sensor = dht.DHT11(Pin(33))   # REQUIRED by lab
relay = Pin(15, Pin.OUT)
relay.off()
# ---------- TEMPERATURE LOGIC ----------
while True:
    try:
        sensor.measure() 
        
        temperature = sensor.temperature()  # °C
        humidity = sensor.humidity()        # %
        
        print("Temperature: {} °C".format(temperature))
        print("Humidity: {} %".format(humidity))
        print("---------------------------")
        
    except OSError:
        print("Failed to read from DHT11 sensor")

    time.sleep(5)  # DHT11 needs at least 1 second delay