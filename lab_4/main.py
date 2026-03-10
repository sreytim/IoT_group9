import network, time, ujson, ubinascii, machine
from umqtt.simple import MQTTClient
from machine import Pin, ADC, I2C

from bmp280 import BMP280
from ds3231 import DS3231
from mlx90614 import MLX90614


SSID = "Zenk1k0"
PASSWORD = "092567088"

BROKER = "broker.hivemq.com"
PORT = 1883
KEEPALIVE = 120

CLIENT_ID = b"aupp_" + ubinascii.hexlify(machine.unique_id())
TOPIC = b"/aupp/esp32/environment"

MQ5_PIN = 33
WINDOW = 5
FEVER_THRESHOLD = 32.5

readings = []


# ---------------------------
# GAS PROCESSING
# ---------------------------

def moving_average(val):
    readings.append(val)
    if len(readings) > WINDOW:
        readings.pop(0)
    return sum(readings) / len(readings)


def classify(avg):
    if avg < 2100:
        return "SAFE", 1
    elif avg < 2600:
        return "WARNING", 2
    else:
        return "DANGER", 3


def fever_detect(body_temp):
    return 1 if body_temp >= FEVER_THRESHOLD else 0


# ---------------------------
# TIME CONVERSION
# ---------------------------

def get_readable_time(t):
    """Converts RTC tuple to YYYY-MM-DD HH:MM:SS string"""
    return "{:04d}-{:02d}-{:02d} {:02d}:{:02d}:{:02d}".format(
        t[0], t[1], t[2], t[3], t[4], t[5]
    )


# ---------------------------
# WIFI CONNECTION
# ---------------------------

def wifi_connect():
    wlan = network.WLAN(network.STA_IF)

    # Fully reset WiFi interface
    wlan.active(False)
    time.sleep(1)
    wlan.active(True)

    if not wlan.isconnected():
        print("Connecting to WiFi...")
        wlan.connect(SSID, PASSWORD)

        timeout = 20
        start = time.time()

        while not wlan.isconnected():
            if time.time() - start > timeout:
                raise RuntimeError("WiFi connection timeout")
            time.sleep(0.5)

    print("WiFi Connected:", wlan.ifconfig())


# ---------------------------
# MQTT CONNECTION
# ---------------------------

def mqtt_connect():
    client = MQTTClient(CLIENT_ID, BROKER, port=PORT, keepalive=KEEPALIVE)
    client.connect()
    print("Connected to MQTT broker:", BROKER)
    return client


# ---------------------------
# MAIN PROGRAM
# ---------------------------

def main():

    wifi_connect()
    client = mqtt_connect()

    # Sensors
    mq5 = ADC(Pin(MQ5_PIN))
    mq5.atten(ADC.ATTN_11DB)
    mq5.width(ADC.WIDTH_12BIT)

    i2c = I2C(0, scl=Pin(22), sda=Pin(21), freq=100000)

    bmp = BMP280(i2c)
    rtc = DS3231(i2c)
    mlx = MLX90614(i2c)

    while True:

        try:

            # Ensure WiFi still connected
            if not network.WLAN(network.STA_IF).isconnected():
                wifi_connect()
                client = mqtt_connect()
                
            try:
                time_tuple = rtc.get_time()
                readable_ts = get_readable_time(time_tuple)
                
                amb_t = round(mlx.read_amb_temp(), 2)
                obj_t = round(mlx.read_object_temp(), 2)
                pres = round(bmp.pressure / 100, 2)
                alt = round(bmp.altitude, 2)
            except Exception as i2c_err:
                print("I2C Sensor Error:", i2c_err)
                time.sleep(2)
                continue
            # -----------------------
            # Read Sensors
            # -----------------------
            raw = mq5.read()
            avg = moving_average(raw)
            risk_label, risk_num = classify(avg)
            
            # -----------------------
            # Payload
            # -----------------------

            payload = {
                "time_str": readable_ts,
                "gas_raw": raw,
                "gas_risk": risk_num,
                "body_temp": obj_t,
                "fever": fever_detect(obj_t),
                "ambient_temp": amb_t,
                "pressure": pres,
                "altitude": alt
            }

            # Publish
            client.publish(TOPIC, ujson.dumps(payload))

            print("Sent:", payload)

        except OSError as e:

            print("Connection lost:", e)

            try:
                client.disconnect()
            except:
                pass

            wifi_connect()
            client = mqtt_connect()

        time.sleep(5)


# ---------------------------
# RUN
# ---------------------------

if __name__ == "__main__":
    main()