import network, urequests, time
from machine import Pin, PWM

# --- CONFIG ---
WIFI_SSID = "Robotic WIFI"
WIFI_PASS = "rbtWIFI@2025"
TOKEN = "cAeyF8Z0r_AxKmFNvyX3A3zVxesJK7O-"
URL = "http://blynk.cloud/external/api"

# --- HARDWARE ---
servo = PWM(Pin(13), freq=50)
ir_sensor = Pin(12, Pin.IN)

def move_servo(angle):
    # Constrain angle to 0-180 to be safe
    angle = max(0, min(180, angle))
    duty = int(26 + (angle / 180) * (128 - 26))
    servo.duty(duty)

# --- WIFI CONNECT ---
wlan = network.WLAN(network.STA_IF)
wlan.active(True)
wlan.connect(WIFI_SSID, WIFI_PASS)
print("Connecting WiFi...")
while not wlan.isconnected():
    time.sleep(0.5)
print("Connected! IP:", wlan.ifconfig()[0])

# --- MAIN LOOP ---
while True:
    try:
        # 1. Check if we are in AUTO or MANUAL mode 
        res_mode = urequests.get(f"{URL}/get?token={TOKEN}&V9")
        if res_mode.status_code == 200:
            val_mode = res_mode.text.strip()
            
            # Validation: Only proceed if Blynk returns a number
            if val_mode.isdigit():
                auto_mode = int(val_mode)
                
                if auto_mode == 1:
                    print("Mode: AUTOMATIC (IR active)")
                    if ir_sensor.value() == 0:  # Object detected
                        move_servo(90)
                        time.sleep(2)
                        move_servo(0)
                else:
                    print("Mode: MANUAL (Slider active)")
                    # 2. Get Slider value
                    res_slider = urequests.get(f"{URL}/get?token={TOKEN}&V5")
                    val_slider = res_slider.text.strip()
                    
                    if val_slider.isdigit():
                        angle = int(val_slider)
                        move_servo(angle)
                    res_slider.close()
            else:
                print(f"Blynk Error (V1): {val_mode}")
        res_mode.close()

    except Exception as e:
        print("Loop Error:", e)
    
    time.sleep(0.5) 