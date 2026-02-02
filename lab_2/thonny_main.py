try:
    import usocket as socket
except:
    import socket

import machine
from machine import Pin, SoftI2C, time_pulse_us
from machine_i2c_lcd import I2cLcd
import network
import esp
import gc
import dht
from time import sleep, sleep_us, ticks_ms, ticks_diff

# --- WiFi Configuration ---
ssid = 'Robotic WIFI'
password = 'rbtWIFI@2025'

# --- Pin & Sensor Configuration ---
led = Pin(2, Pin.OUT)
dht_sensor = dht.DHT11(machine.Pin(4))
TRIG = Pin(27, Pin.OUT)
ECHO = Pin(26, Pin.IN)
I2C_ADDR = 0x27
i2c = SoftI2C(sda=Pin(21), scl=Pin(22), freq=400000)
lcd = I2cLcd(i2c, I2C_ADDR, 2, 16)
lcd.putstr("Connecting WiFi...")

last_distance = None
last_temp = None
last_humidity = None

# --- State flags ---
custom_message_active = False
last_update_time = ticks_ms()

# --- Connect to WiFi ---
station = network.WLAN(network.STA_IF)
station.active(True)
station.connect(ssid, password)
while not station.isconnected():
    pass
print('Connection successful')
print(station.ifconfig())
lcd.clear()
lcd.putstr("Narak's IOT")
sleep(1)

# --- Ultrasonic Distance Function ---
def get_distance_cm():
    TRIG.off(); sleep_us(2)
    TRIG.on();  sleep_us(10)
    TRIG.off()
    t = time_pulse_us(ECHO, 1, 30000)
    if t < 0:
        return None
    return (t * 0.0343) / 2.0

# --- LCD scrolling text ---
def scroll_lcd_text(text):
    global custom_message_active
    custom_message_active = True
    lcd.clear()
    if len(text) <= 16:
        lcd.move_to(0, 0)
        lcd.putstr(text)
        sleep(2)
    else:
        for i in range(len(text) - 15):
            lcd.clear()
            lcd.move_to(0, 0)
            lcd.putstr(text[i:i+16])
            sleep(0.3)
        sleep(2)
    custom_message_active = False

# --- Enhanced Web Page with Dark Glass Theme ---
def web_page(gpio_state):
    global last_distance, last_temp, last_humidity
    dist_display = "N/A"
    temp_display = "N/A"
    humid_display = "N/A"
    if last_distance is not None:
        dist_display = "{:.1f} cm".format(last_distance)
    if last_temp is not None:
        temp_display = "{:.1f} °C".format(last_temp)
    if last_humidity is not None:
        humid_display = "{:.1f} %".format(last_humidity)

    html = """<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>ESP32 Control Panel</title>
  <style>
    * { margin: 0; padding: 0; box-sizing: border-box; }
    body { margin: 0; font-family: 'Segoe UI', sans-serif; background: linear-gradient(135deg, #1d2b64 0%, #f8cdda 100%); color: #fff; display: flex; justify-content: center; align-items: center; min-height: 100vh; padding: 20px; position: relative; overflow-x: hidden; }
    body::before { content: ''; position: absolute; width: 500px; height: 500px; background: rgba(248, 205, 218, 0.1); border-radius: 50%; top: -200px; right: -200px; animation: float 8s ease-in-out infinite; }
    body::after { content: ''; position: absolute; width: 400px; height: 400px; background: rgba(29, 43, 100, 0.1); border-radius: 50%; bottom: -150px; left: -150px; animation: float 10s ease-in-out infinite reverse; }
    @keyframes float { 0%, 100% { transform: translateY(0px); } 50% { transform: translateY(30px); } }
    .container { background: rgba(0, 0, 0, 0.8); backdrop-filter: blur(20px); -webkit-backdrop-filter: blur(20px); border: 1px solid rgba(255, 255, 255, 0.1); border-radius: 25px; padding: 35px; max-width: 420px; width: 90%; text-align: center; box-shadow: 0 15px 35px rgba(0, 0, 0, 0.5), 0 5px 15px rgba(0, 0, 0, 0.3); position: relative; z-index: 1; }
    h1 { margin-bottom: 25px; font-size: 2.2rem; color: #f8cdda; font-weight: 700; text-shadow: 0 2px 10px rgba(248, 205, 218, 0.3); letter-spacing: -0.5px; }
    .status { font-size: 1.15rem; background: linear-gradient(135deg, rgba(255, 255, 255, 0.15), rgba(255, 255, 255, 0.05)); border: 1px solid rgba(255, 255, 255, 0.1); padding: 14px 18px; border-radius: 12px; margin-bottom: 28px; backdrop-filter: blur(10px); box-shadow: 0 4px 15px rgba(0, 0, 0, 0.2); animation: pulse 2s ease-in-out infinite; }
    @keyframes pulse { 0%, 100% { opacity: 1; } 50% { opacity: 0.7; } }
    .status strong { color: #ffc107; font-weight: 700; text-transform: uppercase; letter-spacing: 1.5px; text-shadow: 0 0 10px rgba(255, 193, 7, 0.5); }
    .sensor-box { margin-bottom: 28px; text-align: left; font-size: 1.05rem; line-height: 2.2; background: linear-gradient(135deg, rgba(255, 255, 255, 0.12), rgba(255, 255, 255, 0.06)); border: 1px solid rgba(255, 255, 255, 0.1); padding: 16px 18px; border-radius: 15px; backdrop-filter: blur(10px); box-shadow: 0 4px 15px rgba(0, 0, 0, 0.2); }
    .sensor-box div { display: flex; justify-content: space-between; align-items: center; padding: 6px 0; border-bottom: 1px solid rgba(255, 255, 255, 0.08); }
    .sensor-box div:last-child { border-bottom: none; padding-bottom: 0; }
    .sensor-box div:first-child { padding-top: 0; }
    .sensor-label { color: #f8cdda; font-weight: 600; }
    .sensor-value { color: #ffc107; font-weight: 700; font-size: 1.1rem; text-shadow: 0 0 10px rgba(255, 193, 7, 0.3); }
    .buttons { display: grid; grid-template-columns: 1fr 1fr; gap: 12px; margin-bottom: 28px; }
    .button { padding: 16px 0; border: none; border-radius: 14px; font-size: 0.95rem; font-weight: 700; cursor: pointer; color: #fff; transition: all 0.3s ease; text-decoration: none; display: flex; justify-content: center; align-items: center; box-shadow: 0 4px 15px rgba(0, 0, 0, 0.3); text-transform: uppercase; letter-spacing: 0.5px; }
    .on { background: linear-gradient(135deg, #28a745, #20c997); border: 1px solid rgba(255, 255, 255, 0.2); }
    .off { background: linear-gradient(135deg, #dc3545, #e83e8c); border: 1px solid rgba(255, 255, 255, 0.2); }
    .lcd-action-btn { background: linear-gradient(135deg, rgba(255, 255, 255, 0.25), rgba(255, 255, 255, 0.15)); border: 1px solid rgba(255, 255, 255, 0.3); backdrop-filter: blur(10px); }
    .on:hover { transform: translateY(-3px); box-shadow: 0 8px 25px rgba(40, 167, 69, 0.4); }
    .off:hover { transform: translateY(-3px); box-shadow: 0 8px 25px rgba(220, 53, 69, 0.4); }
    .lcd-action-btn:hover { transform: translateY(-3px); box-shadow: 0 8px 25px rgba(255, 255, 255, 0.2); }
    .lcd-form { border-top: 1px solid rgba(255, 255, 255, 0.15); padding-top: 25px; margin-top: 5px; }
    .lcd-input { width: 100%; padding: 14px 16px; border-radius: 12px; border: 2px solid rgba(255, 255, 255, 0.2); background: rgba(255, 255, 255, 0.1); backdrop-filter: blur(10px); font-size: 1rem; margin-bottom: 12px; color: #fff; transition: all 0.3s ease; }
    .lcd-input::placeholder { color: rgba(255, 255, 255, 0.5); }
    .lcd-input:focus { outline: none; border-color: #ffc107; background: rgba(255, 255, 255, 0.15); box-shadow: 0 0 0 4px rgba(255, 193, 7, 0.1), 0 0 20px rgba(255, 193, 7, 0.2); }
    .submit-btn { width: 100%; background: linear-gradient(135deg, #ffc107, #ff9800); color: #1d2b64; font-weight: 700; border: 1px solid rgba(255, 193, 7, 0.3); }
    .submit-btn:hover { background: linear-gradient(135deg, #ffca28, #ffa726); box-shadow: 0 8px 25px rgba(255, 193, 7, 0.4); color: #000; }
    @media (max-width: 480px) { .container { padding: 28px 22px; } h1 { font-size: 1.9rem; } .buttons { gap: 10px; } .button { font-size: 0.9rem; padding: 14px 0; } }
  </style>
</head>
<body>
  <div class="container">
    <h1>⚡ ESP Control Panel</h1>
    <div class="status">GPIO Status: <strong>""" + gpio_state + """</strong></div>
    <div class="sensor-box">
      <div><span class="sensor-label">📏 Distance</span><span class="sensor-value">""" + dist_display + """</span></div>
      <div><span class="sensor-label">🌡️ Temperature</span><span class="sensor-value">""" + temp_display + """</span></div>
      <div><span class="sensor-label">💧 Humidity</span><span class="sensor-value">""" + humid_display + """</span></div>
    </div>
    <div class="buttons">
      <a href="/?led=on" class="button on">Turn ON</a>
      <a href="/?led=off" class="button off">Turn OFF</a>
      <a href="/?lcd=distance" class="button lcd-action-btn">Show Distance</a>
      <a href="/?lcd=temp" class="button lcd-action-btn">Show Temp</a>
    </div>
    <div class="lcd-form">
      <form action="/" method="get">
        <input type="text" name="lcd_text" class="lcd-input" placeholder="Enter text for LCD display..." maxlength="64">
        <button type="submit" class="button submit-btn">📺 Update LCD</button>
      </form>
    </div>
  </div>
</body>
</html>"""
    return html

# --- Setup Web Server Socket ---
s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
s.bind(('', 80))
s.listen(5)
print("Web server started on port 80")
print("Access at:", station.ifconfig()[0])

# --- Main Loop ---
while True:
    try:
        # --- Update LCD with live sensor data every 2s if no custom text active ---
        if not custom_message_active and ticks_diff(ticks_ms(), last_update_time) > 2000:
            distance = get_distance_cm()
            if distance is not None:
                last_distance = distance
            try:
                dht_sensor.measure()
                temp = dht_sensor.temperature()
                humid = dht_sensor.humidity()
                last_temp = temp
                last_humidity = humid
            except:
                pass

            lcd.clear()
            lcd.move_to(0, 0)
            if last_distance is not None:
                lcd.putstr("Dist:{:>5.1f}cm".format(last_distance))
            else:
                lcd.putstr("Dist: N/A")
            lcd.move_to(0, 1)
            if last_temp is not None and last_humidity is not None:
                lcd.putstr("T:{:>4.1f}C H:{:>3.0f}%".format(last_temp, last_humidity))
            else:
                lcd.putstr("T: N/A H: N/A")
            last_update_time = ticks_ms()

        # --- Handle web requests ---
        conn, addr = s.accept()
        print('Connection from', addr)
        request = conn.recv(1024).decode('utf-8')
        print('Request:', request[:100])

        # LED control
        if '/?led=on' in request:
            led.value(1)
            print('LED turned ON')
        if '/?led=off' in request:
            led.value(0)
            print('LED turned OFF')

        # LCD Sensor Display Control
        if '/?lcd=distance' in request:
            distance = get_distance_cm()
            if distance is not None:
                last_distance = distance
                lcd.clear()
                lcd.putstr("Dist:{:.1f}cm".format(distance))
                print('Distance shown on LCD:', distance)
                
        if '/?lcd=temp' in request:
            try:
                dht_sensor.measure()
                temp = dht_sensor.temperature()
                humid = dht_sensor.humidity()
                last_temp = temp
                last_humidity = humid
                lcd.clear()
                lcd.putstr("Temp:{:.1f}C".format(temp))
                lcd.move_to(0, 1)
                lcd.putstr("Hum:{:.1f}%".format(humid))
                print('Temperature shown on LCD:', temp)
            except Exception as e:
                print('DHT error:', e)

        # Custom text control
        text_param = '/?lcd_text='
        if text_param in request:
            start_index = request.find(text_param) + len(text_param)
            end_index = request.find(' HTTP/')
            if end_index == -1:
                end_index = len(request)
            raw_text = request[start_index:end_index]
            custom_message = raw_text.replace('+', ' ').replace('%20', ' ')
            # URL decode other special characters
            custom_message = custom_message.replace('%21', '!').replace('%3F', '?')
            custom_message = custom_message.replace('%2C', ',').replace('%2E', '.')
            print("Received LCD message:", custom_message)
            scroll_lcd_text(custom_message)

        # --- Send Web Page Response ---
        gpio_state = "ON" if led.value() == 1 else "OFF"
        response = web_page(gpio_state)
        conn.send('HTTP/1.1 200 OK\n')
        conn.send('Content-Type: text/html\n')
        conn.send('Connection: close\n\n')
        conn.sendall(response)
        conn.close()

    except OSError as e:
        conn.close()
        print('Connection error:', e)
        gc.collect()
    except KeyboardInterrupt:
        print('Server stopped by user')
        break
    except Exception as e:
        if 'conn' in locals():
            conn.close()
        print('Error:', e)
        gc.collect()

# Cleanup
s.close()
print('Server closed')
