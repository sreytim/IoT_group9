# IoT_group9
# ESP32 Temperature Monitoring & Telegram Bot

A smart room temperature monitoring system using an ESP32 microcontroller with a DHT22 sensor and relay control. The system monitors temperature and humidity, sends alerts via Telegram, and allows remote control of a compressor relay through bot commands.

## Features

- **Real-time Monitoring**: Reads DHT22 sensor every 5 seconds with temperature and humidity displayed to 2 decimal places
- **Telegram Integration**: Send alerts and receive commands via Telegram bot
- **Smart Relay Control**: Automatic and manual control of compressor based on temperature thresholds
- **Intelligent Alerting**: Sends alerts only when temperature ≥ 30°C and relay is OFF
- **Robust Error Handling**: Auto-reconnect Wi-Fi, graceful handling of sensor/network failures
- **State Management**: Tracks relay state and temperature to prevent redundant messages

## Hardware Requirements

### Components
- **ESP32 Development Board**
- **DHT22 Temperature & Humidity Sensor**
- **Single Relay Module** (active HIGH)
- **Power Supply**: 5V/2A (for ESP32 and relay)
- **Jumper Wires** & **Breadboard** (optional)

### Wiring Diagram

```
ESP32 Pinout & Connections:
┌─────────────────────────────────────┐
│           ESP32 Board               │
├─────────────────────────────────────┤
│ 3V3 ──────────────┐                 │
│                   │                 │
│ D4 (GPIO4) ◄─────┴─── DHT22 Data   │
│            (with 4.7kΩ pull-up)     │
│                                     │
│ D2 (GPIO26) ◄──────── Relay IN      │
│                                     │
│ GND ◄────────────────── DHT22 GND   │
│ GND ◄────────────────── Relay GND   │
│                                     │
└─────────────────────────────────────┘

DHT22 Sensor Connection:
- Pin 1 (VCC) → ESP32 3V3
- Pin 2 (DATA) → ESP32 D4 (GPIO4) with 4.7kΩ pull-up resistor to 3V3
- Pin 3 (NC) → Not connected
- Pin 4 (GND) → ESP32 GND

Relay Module Connection:
- VCC → ESP32 5V (or dedicated 5V supply)
- GND → ESP32 GND
- IN → ESP32 D2 (GPIO26)
- COM → Compressor Power IN
- NO → Compressor Power OUT
```

### Wiring Photo Placeholder
*Place a clear photo of your actual wiring setup here for reference*

## Software Requirements

- **MicroPython** (ESP32 firmware)
- **Libraries**: 
  - `network` (built-in, Wi-Fi connectivity)
  - `urequests` (HTTP requests to Telegram API)
  - `time` (timing and delays)
  - `dht` (DHT22 sensor reading)
  - `machine` (GPIO control)

## Configuration

### 1. Telegram Bot Setup

1. **Create a Telegram Bot**:
   - Open Telegram and search for `@BotFather`
   - Send `/newbot` and follow instructions
   - Copy your **Bot Token** (format: `123456789:ABCdef-GHIJKLMNOPQRSTUVWXYZ`)

2. **Get Your Chat ID**:
   - Add your bot `@sochannimol_bot` to your group chat
   - Send any message in the group
   - Visit: `https://api.telegram.org/bot<YOUR_BOT_TOKEN>/getUpdates`
   - Find your **Chat ID** (group chat IDs are negative numbers)

3. **Update Configuration in Code**:
   - Edit `main.py` and set these variables:
   ```python
   BOT_TOKEN = "YOUR_BOT_TOKEN_HERE"
   CHAT_ID = "YOUR_CHAT_ID_HERE"
   ```

### 2. Wi-Fi Configuration

Edit `main.py` and update:
```python
SSID = "YOUR_SSID"
PASSWORD = "YOUR_PASSWORD"
```

### 3. Hardware Pin Mapping

Current configuration in `main.py`:
```python
DHT_PIN = 4      # D4 (GPIO4)
RELAY_PIN = 26   # D2 (GPIO26)
```

If using different pins, update these values accordingly.

## Usage Instructions

### 1. Upload Code to ESP32

1. Connect ESP32 to your computer via USB
2. Use tools like:
   - **Thonny** (recommended for beginners)
   - **ESPTool** + terminal
   - **Arduino IDE** with MicroPython support

3. Upload `main.py` to the ESP32

4. The system will:
   - Connect to Wi-Fi automatically
   - Start reading DHT22 every 5 seconds
   - Send status to serial monitor

### 2. Monitor via Serial

Open serial monitor at **115200 baud** to see:
```
[Temperature: 28.50°C, Humidity: 65.32%]
[Relay: OFF]
```

### 3. Control via Telegram Bot

Send commands to your group chat:

#### `/status`
Returns current temperature, humidity, and relay state:
```
📊 Current Status:
Temperature: 28.50°C
Humidity: 65.32%
Relay: OFF
```

#### `/on`
Manually turn relay ON (stops automatic alerts):
```
✅ Relay turned ON
```

#### `/off`
Manually turn relay OFF:
```
❌ Relay turned OFF
```

## System Behavior

### Temperature Monitoring Logic

```
┌─────────────────────────────────────────┐
│      Read Temperature Every 5s          │
└────────┬────────────────────────────────┘
         │
         ▼
    T < 30°C?
    ├─ YES: No alerts, relay stays OFF
    │
    └─ NO (T ≥ 30°C):
       ├─ Relay OFF? → Send alert every 5s
       │              (until /on received)
       │
       └─ Relay ON? → Stop alerts
                     ├─ T drops < 30°C?
                     │  → Auto-turn OFF relay
                     │  → Send "auto-OFF" notice
                     │
                     └─ Keep running until manual /off
```

### State Transitions

| Current State | Condition | Action | Next State |
|---|---|---|---|
| T < 30°C, Relay OFF | - | No alerts | Idle |
| T ≥ 30°C, Relay OFF | - | Send alert every 5s | Alert Loop |
| Alert Loop | `/on` received | Turn relay ON, stop alerts | Running |
| Relay ON | T < 30°C | Auto-turn OFF, send notice | Idle |
| Relay ON | `/off` received | Turn relay OFF | Idle |

## Error Handling & Robustness

### Wi-Fi Disconnection
- **Automatic reconnection** attempts every 30 seconds
- System continues reading sensor during disconnection
- Alerts resume once connection is restored

### Sensor Errors (DHT22 OSError)
- Skips the current read cycle
- Continues on next interval
- No crash or halt

### Telegram Network Errors
- Prints error status to serial
- Skips the failed cycle
- Continues monitoring
- Retries on next cycle

Example error handling:
```python
try:
    response = urequests.post(url, json=data)
except Exception as e:
    print(f"[ERROR] Telegram send failed: {e}")
    # Continue to next cycle
```

## Troubleshooting

### No Temperature Reading
- **Check DHT22 wiring**: Data pin to D4, VCC to 3V3, GND to GND
- **Verify 4.7kΩ pull-up resistor** between D4 and 3V3
- **Check serial monitor** for DHT error messages

### Relay Not Responding
- **Check GPIO26 (D2) connection** to relay IN pin
- **Verify relay power supply** (5V connected)
- **Test relay manually** by sending `/on` command
- **Check relay polarity**: Ensure active HIGH configuration

### Telegram Not Receiving Messages
- **Verify Bot Token and Chat ID** in `main.py`
- **Check Wi-Fi connection**: Serial monitor should show connected IP
- **Test bot**: Send a message in the group, then visit `getUpdates` URL
- **Firewall**: Ensure ESP32 can reach `api.telegram.org`

### Wi-Fi Won't Connect
- **Check SSID and Password** (case-sensitive)
- **Verify Wi-Fi signal strength** near ESP32
- **Restart ESP32** and try again
- **Check serial monitor** for connection attempts

## Project Structure

```
esp32-temp-bot/
├── main.py                 # Main application code
├── README.md              # This file
├── wiring_diagram.png     # Hardware connection photo
└── docs/
    └── flowchart.png      # State machine diagram
```

## Configuration Reference

| Variable | Default | Description |
|----------|---------|-------------|
| `SSID` | `"YOUR_SSID"` | Wi-Fi network name |
| `PASSWORD` | `"YOUR_PASSWORD"` | Wi-Fi password |
| `BOT_TOKEN` | `"YOUR_TOKEN"` | Telegram bot token |
| `CHAT_ID` | `"YOUR_CHAT_ID"` | Group chat ID |
| `DHT_PIN` | `4` | GPIO pin for DHT22 data |
| `RELAY_PIN` | `26` | GPIO pin for relay control |
| `TEMP_THRESHOLD` | `30` | Alert temperature (°C) |
| `READ_INTERVAL` | `5` | Sensor read interval (seconds) |

## Performance Specifications

- **Sensor Read Interval**: 5 seconds
- **Telegram Update Check**: 5 seconds
- **Alert Frequency**: Every 5 seconds (when T ≥ 30°C)
- **Temperature Precision**: 2 decimal places
- **Humidity Precision**: 2 decimal places
- **Response Time**: < 1 second for commands

## Safety Considerations

⚠️ **Important**:
- Ensure relay module can handle compressor power requirements
- Use proper power supply (5V/2A minimum)
- Do not exceed relay rating (typically 10A @ 250V AC)
- Install thermal overload protection on compressor circuit
- Keep ESP32 away from moisture near compressor

## Future Enhancements

- [ ] Dashboard web interface
- [ ] Historical data logging to SD card
- [ ] Temperature graph visualization
- [ ] Multiple sensor support
- [ ] Custom alert thresholds via Telegram
- [ ] Energy consumption tracking
- [ ] Over-temperature auto-shutdown safety feature

## License

Educational Project - 2025

## Support & Questions

For issues or questions:
1. Check the **Troubleshooting** section
2. Verify wiring against the diagram
3. Check serial monitor output
4. Review code comments in `main.py`

---

**Last Updated**: January 2025  
**Author**: [Your Name]  
**Course**: [Course Code/Name]
