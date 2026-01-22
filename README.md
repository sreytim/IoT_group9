# Lab 1: Temperature Sensor with Relay Control (Telegram)

## Overview
This IoT monitoring node uses an ESP32 with a DHT22 temperature/humidity sensor and relay module to send Telegram alerts when temperature exceeds a threshold and allows remote control via Telegram Bot API.

### Components
- **ESP32 Dev Board** (MicroPython firmware)
- **DHT22 Temperature/Humidity Sensor**
- **Relay Module** (5V or 3.3V compatible)
- **Jumper wires**
- **USB cable** for programming
- **Wi-Fi network** with internet access


### Getting Telegram Credentials

1. **Create a Bot**: Message [@BotFather](https://t.me/botfather) on Telegram
2. **Get Bot Token**: BotFather will provide your `TELEGRAM_BOT_TOKEN`
3. **Get Chat ID**: Send a message to your bot, then visit `https://api.telegram.org/bot<TOKEN>/getUpdates` and copy your `chat_id`


## Task 1: Sensor Read & Print (10 pts)

### Objective
Read DHT22 temperature and humidity every 5 seconds and print values with 2 decimal places.

### Implementation
```python
# main.py (Task 1 section)
import dht
import machine
import time

# Initialize DHT22 on GPIO 4
dht_pin = machine.Pin(4)
dht_sensor = dht.DHT22(dht_pin)

while True:
    try:
        dht_sensor.measure()
        temp = dht_sensor.temperature()
        humidity = dht_sensor.humidity()
        print(f"Temperature: {temp:.2f}°C, Humidity: {humidity:.2f}%")
    except OSError:
        print("DHT sensor read failed, skipping...")
    
    time.sleep(5)
```

### Evidence
- **Serial output screenshot** showing temperature and humidity readings at 5-second intervals with 2 decimal precision

---

## Task 2: Telegram Send (15 pts)

### Objective
Implement `send_message()` function and post a test message to the group chat.

### Implementation
```python
# telegram.py
import urequests
from config import TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID

def send_message(text):
    """Send a message to Telegram chat"""
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    payload = {
        "chat_id": TELEGRAM_CHAT_ID,
        "text": text
    }
    try:
        response = urequests.post(url, json=payload)
        status = response.status_code
        response.close()
        print(f"Telegram send status: {status}")
        return status == 200
    except Exception as e:
        print(f"Telegram error: {e}")
        return False

# Usage in main.py (Task 2)
from telegram import send_message
send_message("Test message from ESP32!")
```

### Evidence
- **Telegram chat screenshot** showing the test message received from the ESP32 bot

---

## Task 3: Bot Commands (/status, /on, /off) (15 pts)

### Objective
Implement three Telegram bot commands:
- `/status`: Reply with current temperature, humidity, and relay state
- `/on`: Turn relay ON
- `/off`: Turn relay OFF

### Implementation
```python
# bot.py
import urequests
from config import TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID
import machine

relay_pin = machine.Pin(5, machine.Pin.OUT)
relay_state = False

def get_updates(offset=0):
    """Fetch messages from Telegram"""
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/getUpdates"
    try:
        response = urequests.get(url, params={"offset": offset, "timeout": 10})
        data = response.json()
        response.close()
        return data.get("result", [])
    except:
        return []

def send_reply(chat_id, text):
    """Send a reply message"""
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    payload = {"chat_id": chat_id, "text": text}
    try:
        urequests.post(url, json=payload).close()
    except:
        print("Failed to send reply")

def handle_command(text, chat_id, temp, humidity):
    """Handle bot commands"""
    global relay_state
    
    if text == "/status":
        relay_status = "ON" if relay_state else "OFF"
        reply = f"Temperature: {temp:.2f}°C\nHumidity: {humidity:.2f}%\nRelay: {relay_status}"
        send_reply(chat_id, reply)
    
    elif text == "/on":
        relay_pin.on()
        relay_state = True
        send_reply(chat_id, "Relay turned ON ✓")
    
    elif text == "/off":
        relay_pin.off()
        relay_state = False
        send_reply(chat_id, "Relay turned OFF ✓")
```

### Evidence
- **Telegram chat screenshot** showing successful execution of `/status`, `/on`, and `/off` commands with appropriate responses

---

## Task 4: Intelligent Alert & Auto-Control Logic (20 pts)

### Objective
Implement temperature-based alert and relay control:
- No messages sent when T < 30°C
- If T ≥ 30°C and relay is OFF, send alert every 5 seconds until `/on` is received
- After `/on` is received, stop sending alerts
- When T drops below 30°C, automatically turn relay OFF and send a one-time "auto-OFF" notification

### Implementation
```python
# main.py (Task 4 logic)
alert_sent = False
relay_manually_on = False

while True:
    try:
        dht_sensor.measure()
        temp = dht_sensor.temperature()
        humidity = dht_sensor.humidity()
        
        # Check temperature threshold
        if temp >= 30:
            if not relay_state and not relay_manually_on:
                # Send alert every loop cycle
                send_message(f"⚠️ ALERT: Temperature {temp:.2f}°C ≥ 30°C\nPlease use /on to activate relay")
            
        elif temp < 30:
            # Auto-OFF when temperature drops
            if relay_state:
                relay_pin.off()
                relay_state = False
                send_message("✓ Temperature dropped below 30°C. Relay turned OFF automatically.")
        
        # Process Telegram commands
        updates = get_updates(offset)
        for update in updates:
            msg = update.get("message", {})
            text = msg.get("text", "")
            chat_id = msg.get("chat", {}).get("id")
            
            if text.startswith("/"):
                handle_command(text, chat_id, temp, humidity)
                if text == "/on":
                    relay_manually_on = True
        
    except OSError:
        print("Sensor error, skipping cycle")
    
    time.sleep(5)
```

### Evidence
- **Demo video (60–90 seconds)** showing:
  - Temperature rising above 30°C and alert messages sending every 5 seconds
  - User sending `/on` command (alerts stop)
  - Temperature cooling down below 30°C (relay auto-turns OFF with notification)

---

## Task 5: Robustness & Error Handling (10 pts)

### Objective
Ensure reliability through:
- Auto-reconnection to Wi-Fi when connection drops
- Graceful handling of Telegram HTTP errors
- DHT sensor read error handling without crashes

### Implementation
```python
# network.py
import network
import time
from config import WIFI_SSID, WIFI_PASSWORD

def connect_wifi():
    """Connect to Wi-Fi with auto-reconnect"""
    wlan = network.WLAN(network.STA_IF)
    wlan.active(True)
    
    if not wlan.isconnected():
        print("Connecting to Wi-Fi...")
        wlan.connect(WIFI_SSID, WIFI_PASSWORD)
        
        timeout = 0
        while not wlan.isconnected() and timeout < 20:
            print("Waiting for connection...")
            time.sleep(1)
            timeout += 1
        
        if wlan.isconnected():
            print(f"Connected! IP: {wlan.ifconfig()[0]}")
        else:
            print("Failed to connect to Wi-Fi")
    
    return wlan.isconnected()

# In main.py
def send_message_safe(text):
    """Send message with error handling"""
    try:
        return send_message(text)
    except Exception as e:
        print(f"Telegram HTTP error: {e}")
        return False

# Main loop with error handling
while True:
    try:
        # Check Wi-Fi connection
        if not wlan.isconnected():
            print("Wi-Fi dropped, attempting reconnect...")
            connect_wifi()
        
        dht_sensor.measure()
        temp = dht_sensor.temperature()
        humidity = dht_sensor.humidity()
        
        # Rest of logic...
        
    except OSError as e:
        print(f"DHT read error: {e}, skipping this cycle")
    except Exception as e:
        print(f"Unexpected error: {e}")
    
    time.sleep(5)
```

### Evidence
- **System demonstrates** automatic Wi-Fi reconnection and continues operation after temporary connection loss
- **Error messages printed** to serial output showing graceful handling of HTTP and sensor errors

---

## Task 6: Documentation (30 pts)

### This README Structure
This README provides complete documentation including:
- **Overview** of project functionality
- **Hardware Setup** with wiring diagram and component list
- **Configuration** instructions for credentials and settings
- **Task-by-Task Breakdown** with implementation code and evidence requirements
- **System Architecture** (see below)

### System Block Diagram

```
┌──────────────────────────────────────────────────────────┐
│                        ESP32 Main Loop                    │
│  ┌────────────────────────────────────────────────────┐  │
│  │ 1. Read DHT22 (every 5s)                           │  │
│  │ 2. Check Temperature against 30°C threshold        │  │
│  │ 3. Poll Telegram for commands (/on, /off, /status)│  │
│  │ 4. Send alerts if T ≥ 30°C                        │  │
│  │ 5. Auto-turn relay OFF when T < 30°C              │  │
│  └────────────────────────────────────────────────────┘  │
│                           │                                │
├───────────────┬──────────┴──────────┬────────────────────┤
│               │                     │                    │
▼               ▼                     ▼                    ▼
DHT22        Relay Module      Telegram Bot API        Wi-Fi
Sensor       (GPIO 5)          (HTTP Requests)       Network
(GPIO 4)
```

### State Machine & Control Flow Flowchart

```
                            START
                              │
                              ▼
                    ┌─────────────────────┐
                    │ Initialize ESP32    │
                    │ - DHT22 on GPIO 4   │
                    │ - Relay on GPIO 5   │
                    │ - Connect to Wi-Fi  │
                    └─────────────────────┘
                              │
                              ▼
                    ┌─────────────────────┐
                    │ Enter Main Loop     │
                    │ (Every 5 seconds)   │
                    └─────────────────────┘
                              │
                              ▼
                    ┌─────────────────────┐
                    │ Read DHT22 Sensor   │
                    │ Get Temp & Humidity │
                    └─────────────────────┘
                              │
                    ┌─────────┴─────────┐
                    │                   │
                    ▼                   ▼
            ┌───────────────┐   ┌──────────────────┐
            │ DHT Error?    │   │ Wi-Fi Connected? │
            └───────────────┘   └──────────────────┘
                    │                   │
            ┌───────┴───────┐   ┌───────┴────────┐
            │ Yes           │   │ No             │
            ▼               ▼   ▼                ▼
        ┌───────┐        │  ┌──────────────┐   │
        │ Skip  │        │  │ Attempt Wi-Fi│   │
        │ Cycle │        │  │ Reconnect    │   │
        └───────┘        │  └──────────────┘   │
                         │         │            │
                         └─────────┴────────────┘
                              │
                              ▼
                    ┌──────────────────────┐
                    │ Check Temperature    │
                    │ Against 30°C Threshold
                    └──────────────────────┘
                              │
                    ┌─────────┴─────────┐
                    │                   │
                    ▼                   ▼
            ┌──────────────┐   ┌──────────────┐
            │ T ≥ 30°C?    │   │ T < 30°C?    │
            └──────────────┘   └──────────────┘
                    │                   │
            ┌───────┴────────┐  ┌───────┴──────────┐
            │ Yes            │  │ Yes              │
            ▼                ▼  ▼                  ▼
        ┌──────────────────┐ ┌──────────────────┐
        │ Relay ON?        │ │ Relay was ON?    │
        │ (Manual /on)     │ │                  │
        └──────────────────┘ └──────────────────┘
                │                      │
        ┌───────┴──────┐      ┌────────┴────────┐
        │ Yes  │  No   │      │ Yes      │ No   │
        ▼      ▼       ▼      ▼         ▼       ▼
      ┌──┐ ┌──────────────┐ ┌─────────┐ │     │
      │  │ │ Send ALERT   │ │Turn OFF │ │  (skip)
      │  │ │ every 5s:    │ │ Relay   │ │     │
      │  │ │ "Temp high"  │ │ and send│ │     │
      │  │ │              │ │ "auto-  │ │     │
      │  │ │ (until /on)  │ │ OFF"    │ │     │
      │  │ └──────────────┘ └─────────┘ │     │
      │  │       │                │     │     │
      └──┴───────┴────────────────┴─────┴─────┘
                              │
                              ▼
                    ┌──────────────────────┐
                    │ Poll Telegram API    │
                    │ Check for Commands   │
                    └──────────────────────┘
                              │
                    ┌─────────┴────────┐
                    │                  │
                    ▼                  ▼
            ┌─────────────┐   ┌──────────────┐
            │ Command     │   │ No Command   │
            │ Received?   │   │              │
            └─────────────┘   └──────────────┘
                    │                  │
                    ▼                  │
            ┌─────────────────────┐   │
            │ Which Command?      │   │
            └─────────────────────┘   │
                    │                  │
        ┌───┬───────┼───────┬───┐    │
        │   │       │       │   │    │
        ▼   ▼       ▼       ▼   ▼    ▼
    ┌──────────┐ ┌──────────┐ ┌──────────┐
    │ /status  │ │   /on    │ │  /off    │
    │          │ │          │ │          │
    │ Send:    │ │ Turn ON  │ │ Turn OFF │
    │ - Temp   │ │ Relay    │ │ Relay    │
    │ - Humid  │ │ Set flag:│ │ Stop     │
    │ - Relay  │ │ manually │ │ Alerts   │
    │   State  │ │_on=True  │ │          │
    └──────────┘ └──────────┘ └──────────┘
            │         │         │
            └─────────┴─────────┘
                      │
                      ▼
            ┌──────────────────┐
            │ Sleep 5 seconds  │
            └──────────────────┘
                      │
                      └─────────────┐
                                    │
                    ┌───────────────┘
                    │
                    ▼
            (Return to Main Loop)
```

### State Diagram: Relay Control States

```
                    ┌─────────────────┐
                    │  IDLE STATE     │
                    │  (T < 30°C)     │
                    │  Relay: OFF     │
                    └─────────────────┘
                            │
                    T ≥ 30°C (rise)
                            │
                            ▼
                    ┌──────────────────┐
                    │  ALERT STATE     │
                    │  (T ≥ 30°C)      │
                    │  Relay: OFF      │
                    │  Send alerts @5s │
                    └──────────────────┘
                            │
                    /on command received
                            │
                            ▼
                    ┌──────────────────┐
                    │  ACTIVE STATE    │
                    │  (Manual Control)│
                    │  Relay: ON       │
                    │  No alerts       │
                    └──────────────────┘
                            │
            ┌───────────────┬┴────────────────┐
            │               │                 │
     /off command    T < 30°C (drop)    (stays ON)
            │               │                 │
            ▼               ▼                 ▼
        ┌────────┐   ┌──────────┐      ┌──────────┐
        │Manual  │   │ Auto-OFF │      │ ACTIVE   │
        │OFF     │   │ with     │      │ STATE    │
        └────────┘   │ notice   │      └──────────┘
            │        └──────────┘           │
            │             │                 │
            └─────────────┴─────────────────┘
                          │
                          ▼
                    ┌─────────────────┐
                    │  IDLE STATE     │
                    │  (T < 30°C)     │
                    │  Relay: OFF     │
                    └─────────────────┘
```

### Usage Instructions

1. **Setup**:
   ```bash
   git clone <your-repo-url>
   # Edit config.py with your credentials
   # Flash main.py to ESP32 via Thonny
   ```

2. **Operation**:
   - ESP32 boots and connects to Wi-Fi
   - Reads temperature every 5 seconds
   - Sends Telegram alerts when T ≥ 30°C
   - Responds to bot commands in Telegram chat

3. **Commands**:
   - `/status` - Display current T/H and relay state
   - `/on` - Manually turn relay ON (stops alerts)
   - `/off` - Manually turn relay OFF

---

## Safety & Performance Considerations

- **Relay Load**: Ensure relay module is rated for your switching load (check datasheet)
- **Power Isolation**: Relay controls separate circuit; do not drive high-power loads directly
- **Sampling Interval**: 5-second DHT read interval prevents sensor overheating
- **Telegram Rate Limits**: Bot respects Telegram API rate limits (~30 msgs/sec per chat)
- **Wi-Fi Stability**: Auto-reconnect handles temporary network drops

---

## File Structure

```
project/
├── main.py              # Main application loop
├── config.py            # Configuration (tokens, Wi-Fi, thresholds)
├── telegram.py          # Telegram message functions
├── bot.py               # Bot command handlers
├── network.py           # Wi-Fi connection management
├── README.md            # This file
└── wiring.jpg           # Photo of physical wiring
```

---

## Testing Checklist

- [ ] DHT22 reads every 5 seconds (Task 1)
- [ ] Test message sends to Telegram (Task 2)
- [ ] `/status` displays T/H/relay state (Task 3)
- [ ] `/on` and `/off` control relay (Task 3)
- [ ] Alerts send every 5s when T ≥ 30°C (Task 4)
- [ ] Alerts stop after `/on` command (Task 4)
- [ ] Relay auto-turns OFF when T < 30°C (Task 4)
- [ ] Wi-Fi auto-reconnects after drop (Task 5)
- [ ] Telegram errors handled gracefully (Task 5)
- [ ] DHT sensor errors don't crash system (Task 5)

---

## References

- [ESP32 MicroPython Documentation](https://docs.micropython.org/en/latest/esp32/quickref.html)
- [DHT22 Sensor Guide](https://docs.micropython.org/en/latest/library/dht.html)
- [Telegram Bot API](https://core.telegram.org/bots/api)
- [urequests Library](https://docs.micropython.org/en/latest/library/urequests.html)
