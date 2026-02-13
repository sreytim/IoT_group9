from machine import Pin, PWM
import network, urequests, time

# --- SETUP ---
WIFI_SSID = "Robotic WIFI"
WIFI_PASS = "rbtWIFI@2025"
BLYNK_TOKEN = "cAeyF8Z0r_AxKmFNvyX3A3zVxesJK7O-"
URL = "http://blynk.cloud/external/api"

servo = PWM(Pin(13), freq=50)
last_angle = -1  # Track last position to prevent unnecessary movement

def set_servo_angle(angle):
    duty = int(26 + (angle / 180) * (128 - 26))
    servo.duty(duty)

# --- CONNECT ---
wlan = network.WLAN(network.STA_IF)
wlan.active(True)
wlan.connect(WIFI_SSID, WIFI_PASS)
while not wlan.isconnected(): time.sleep(0.5)
print("Connected!")

# --- LOOP ---
while True:
    try:
        res = urequests.get(f"{URL}/get?token={BLYNK_TOKEN}&V6")
        if res.status_code == 200:
            new_angle = int(res.text)
            
            # Only move if the slider actually moved
            if abs(new_angle - last_angle) > 1: 
                print(f"Moving to: {new_angle}")
                set_servo_angle(new_angle)
                last_angle = new_angle
                
        res.close()
    except:
        pass
    
    time.sleep(0.4)