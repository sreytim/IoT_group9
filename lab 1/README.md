# Lab 1: Temperature Sensor with Relay Control (Telegram)

## Overview

This IoT monitoring node uses an ESP32 with a DHT22 temperature/humidity sensor and relay module to send Telegram alerts when temperature exceeds a threshold and allows remote control via Telegram Bot API.

## Components

- **ESP32 Dev Board** (MicroPython firmware)
- **DHT22 Temperature/Humidity Sensor**
- **Relay Module** (5V or 3.3V compatible)
- **Jumper wires**
- **USB cable** for programming
- **Wi-Fi network** with internet access

## Getting Telegram Credentials

1. **Create a Bot**: Message [@BotFather](https://t.me/botfather) on Telegram
2. **Get Bot Token**: BotFather will provide your `TELEGRAM_BOT_TOKEN`
3. **Get Chat ID**: Send a message to your bot, then visit `https://api.telegram.org/bot<TOKEN>/getUpdates` and copy your `chat_id`

## Flowchart

![Flowchart](images/flowchart.png)

## Task 1: Sensor Read & Print

### Objective

Read DHT22 temperature and humidity every 5 seconds and print values with 2 decimal places.

### Evidence

![Task 1 Wiring Setup](images/task 1.png)

## Task 2: Telegram Send

### Objective

Implement `send_message()` function and post a test message to the group chat.

### Evidence

![Task 2 Wiring Setup](images/task 2.png)

![Task 2 Terminal Output](images/task 2_terminal.png)

## Task 3: Bot Commands (/status, /on, /off)

### Objective

Implement three Telegram bot commands:

- `/status`: Reply with current temperature, humidity, and relay state
- `/on`: Turn relay ON
- `/off`: Turn relay OFF

### Evidence

![Task 3 Wiring Setup](images/task 3.png)

## Task 4: Intelligent Alert & Auto-Control Logic

### Objective

Implement temperature-based alert and relay control:

- No messages sent when T < 30°C
- If T ≥ 30°C and relay is OFF, send alert every 5 seconds until `/on` is received
- After `/on` is received, stop sending alerts
- When T drops below 30°C, automatically turn relay OFF and send a one-time "auto-OFF" notification

### Evidence

**Video Demonstration**: [YouTube Link](https://youtu.be/FpNv4iB8RDQ?si=KWKbDiEc0fcDbF5W)

The demonstration shows:
- Temperature rising above 30°C and alert messages sending every 5 seconds
- User sending `/on` command (alerts stop)
- Temperature cooling down below 30°C (relay auto-turns OFF with notification)

## Installation & Usage

### Setup

```bash
git clone https://github.com/sreytim/IoT_group9.git

```

### Operation

1. ESP32 boots and connects to Wi-Fi
2. Reads temperature every 5 seconds
3. Sends Telegram alerts when T ≥ 30°C
4. Responds to bot commands in Telegram chat

### Commands

- `/status` - Display current temperature/humidity and relay state
- `/on` - Manually turn relay ON (stops alerts)
- `/off` - Manually turn relay OFF

