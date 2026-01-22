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


## Task 1: Sensor Read & Print

### Objective
Read DHT22 temperature and humidity every 5 seconds and print values with 2 decimal places.

### Evidence
![Task 1 Wiring Setup](images/task%201)

## Task 2: Telegram Send

### Objective
Implement `send_message()` function and post a test message to the group chat.

### Evidence
![Task 2 Wiring Setup](images/task%202)
![Task 2(terminal) Wiring Setup](images/task%202%28terminal%29)

## Task 3: Bot Commands (/status, /on, /off) 

### Objective
Implement three Telegram bot commands:
- `/status`: Reply with current temperature, humidity, and relay state
- `/on`: Turn relay ON
- `/off`: Turn relay OFF

### Evidence
![Task 3 Wiring Setup](images/task%203)

## Task 4: Intelligent Alert & Auto-Control Logic (20 pts)

### Objective
Implement temperature-based alert and relay control:
- No messages sent when T < 30°C
- If T ≥ 30°C and relay is OFF, send alert every 5 seconds until `/on` is received
- After `/on` is received, stop sending alerts
- When T drops below 30°C, automatically turn relay OFF and send a one-time "auto-OFF" notification

### Evidence
  - Temperature rising above 30°C and alert messages sending every 5 seconds
  - User sending `/on` command (alerts stop)
  - Temperature cooling down below 30°C (relay auto-turns OFF with notification)

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
