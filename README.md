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
