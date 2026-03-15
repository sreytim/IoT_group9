# 🅿️ Smart IoT Parking Management System

> Built on ESP32 with MicroPython | Telegram + Web Dashboard + Blynk

---

## Table of Contents

1. [Introduction](#1-introduction)
2. [Hardware Description](#2-hardware-description)
3. [System Architecture](#3-system-architecture)
4. [Software Architecture](#4-software-architecture)
5. [IoT Integration](#5-iot-integration)
6. [Working Process](#6-working-process)
7. [Challenges Faced](#7-challenges-faced)
8. [Future Improvements](#8-future-improvements)
9. [Conclusion](#9-conclusion)

---

## 1. Introduction

The **Smart IoT Parking Management System (SIPMS)** is a fully integrated embedded system designed to automate and monitor a parking facility in real time. Built on an ESP32 microcontroller running MicroPython, the system combines multiple sensors, actuators, and three IoT platforms to provide a seamless parking management experience accessible from any device.

The system addresses common urban parking challenges: wasted time searching for spaces, lack of remote visibility, manual gate operation, and poor environmental monitoring. By integrating ultrasonic sensing, IR occupancy detection, servo-controlled gate automation, and cloud connectivity, this project demonstrates a practical end-to-end IoT solution.

### 1.1 Project Objectives

- Automate vehicle entry detection and gate control using ultrasonic sensor and servo motor
- Monitor real-time parking slot occupancy using IR sensors
- Provide multi-platform control via Telegram Bot, Web Dashboard, and Blynk App
- Monitor environmental conditions (temperature and humidity) using DHT11 sensor
- Display live parking information on TM1637 seven-segment display and I2C LCD
- Implement intelligent LED lighting automation based on temperature threshold

### 1.2 System Overview

The system operates on three layers:

| Layer | Description |
|---|---|
| **Hardware Layer** | Sensors and actuators physically connected to the ESP32 |
| **Firmware Layer** | MicroPython async tasks managing all hardware in real time |
| **Cloud Layer** | Telegram, Web Server, and Blynk providing remote monitoring and control |

---

## 2. Hardware Description

| Component | Pin(s) | Function |
|---|---|---|
| **ESP32 (MicroPython)** | — | Main microcontroller. Runs all async tasks, hosts web server, manages WiFi. |
| **HC-SR04 Ultrasonic** | TRIG: 5, ECHO: 18 | Detects incoming vehicles at the gate entrance. Triggers gate open when object is within 15 cm. |
| **IR Sensor x4** | 32, 33, 12, 14 | Detects occupancy of each individual parking slot. Active LOW with internal pull-up. |
| **SG90 Servo Motor** | PWM: 25 | Controls the physical gate barrier. 0° = closed, 90° = open. |
| **DHT11 Sensor** | 4 | Measures ambient temperature and humidity every 4 seconds. Used for LED auto control. |
| **TM1637 7-Segment** | CLK: 15, DIO: 2 | Displays the number of available parking slots as a single digit in real time. |
| **I2C LCD 16x2** | SDA: 21, SCL: 22 | Shows system status: slot count, gate state, temperature, humidity, and LED state. |
| **Built-in LED** | GPIO 2 | Simulates parking lot lighting. Controlled manually or automatically by temperature. |

### 2.1 Wiring Notes

- All IR sensors use `PULL_UP` configuration — a reading of `0` means a car is detected (slot occupied)
- The servo PWM frequency is set to 50 Hz. Pulse width ranges from 500 µs (0°) to 2500 µs (180°)
- The LCD communicates over SoftI2C at 100 kHz. Supported I2C addresses: `0x27` or `0x3F`
- The DHT11 requires a minimum of 4 seconds between readings to avoid checksum errors
- The TM1637 display uses a custom MicroPython library (`tm1637.py`) which must be uploaded to the ESP32

---

## 3. System Architecture

### 3.1 Architecture Overview

```
┌─────────────────────────────────────────────────────────────────┐
│                        ESP32 (MicroPython)                      │
│                                                                 │
│  ┌──────────────┐   ┌──────────────────┐   ┌────────────────┐  │
│  │ HARDWARE     │   │ FIRMWARE         │   │ WEB SERVER     │  │
│  │              │   │                  │   │                │  │
│  │ HC-SR04      │──▶│ task_sensors()   │   │ /             │  │
│  │ IR x4        │──▶│ task_gate_auto() │   │ /status       │  │
│  │ Servo        │◀──│ wifi_manager()   │   │ /open         │  │
│  │ DHT11        │──▶│ web_server()     │──▶│ /close        │  │
│  │ TM1637       │◀──│ task_tm1637()    │   │ /led_on       │  │
│  │ LCD I2C      │◀──│                  │   │ /led_off      │  │
│  │ Built-in LED │◀──│                  │   │ /led_auto     │  │
│  └──────────────┘   └──────────────────┘   └───────┬────────┘  │
└──────────────────────────────────────────────────────┼──────────┘
                                                       │ HTTP
                              ┌────────────────────────┼──────────────┐
                              │        bridge.py (Laptop)             │
                              │                                       │
                              │  ┌─────────────┐  ┌───────────────┐  │
                              │  │ Telegram Bot │  │  Blynk Loop   │  │
                              │  │ (async)      │  │  (thread)     │  │
                              │  └──────┬───────┘  └──────┬────────┘  │
                              └─────────┼─────────────────┼───────────┘
                                        │                 │
                               Telegram API          Blynk Cloud
```

### 3.2 Async Task Structure

| Task | Period | Responsibility |
|---|---|---|
| `task_sensors()` | 250 ms | Read IR, ultrasonic, DHT11. Update LED in AUTO mode. Update LCD. |
| `task_gate_automation()` | 150 ms | Count near/far distance events. Auto-open and auto-close gate. |
| `task_tm1637_display()` | 1500 ms | Show available slot count on 7-segment display. |
| `wifi_manager()` | 6000 ms | Maintain WiFi connection. Reconnect if disconnected. |
| `web_server()` | 3000 ms | Start HTTP server once WiFi is ready. Serve dashboard and handle API. |

### 3.3 State Dictionary

All system state is stored in a single shared dictionary readable and writable by all tasks and web handlers:

```python
state = {
    "slots":             0,        # Free parking slots (0–4)
    "gate":              "CLOSED", # Gate state: 'OPEN' or 'CLOSED'
    "temp":              None,     # DHT11 temperature (°C) or None
    "hum":               None,     # DHT11 humidity (%) or None
    "led":               0,        # LED state: 0 = OFF, 1 = ON
    "led_mode":          "AUTO",   # LED control: 'MANUAL' or 'AUTO'
    "last_distance_cm":  None,     # Median-filtered ultrasonic reading
    "ip":                None,     # Current ESP32 IP address
    "wifi":              False,    # WiFi connection status
}
```

---

## 4. Software Architecture

### 4.1 ESP32 Firmware (`main.py`)

The firmware is written in MicroPython and structured as cooperative async tasks managed by `uasyncio`. The main entry point starts all tasks and enters a garbage collection loop.

#### Gate Automation Logic

The gate uses a debounced counter to prevent false triggers:

- `near_count` increments when `distance < 15 cm` AND `slots > 0`
- Gate **opens** when `near_count` reaches 3 consecutive readings (3 × 150 ms = 450 ms confirmation)
- `far_count` increments when `distance > 20 cm` after gate has been open for at least 3 seconds
- Gate **closes** when `far_count` reaches 3 and minimum hold time has elapsed
- If parking is **full** (`slots == 0`), the gate will not open automatically

#### LED Control Logic

The LED has three operating modes with strict separation so AUTO never overrides a manual command:

| Mode | Behaviour |
|---|---|
| **LED ON** | Sets `led_mode = 'MANUAL'`, LED turns ON immediately. AUTO loop is completely skipped. |
| **LED OFF** | Sets `led_mode = 'MANUAL'`, LED turns OFF immediately. AUTO loop is completely skipped. |
| **LED AUTO** | Sets `led_mode = 'AUTO'`, temperature loop takes control with deadband hysteresis. |

AUTO deadband rules:
- Turns **ON** when `temp > 30°C` and LED is currently OFF
- Turns **OFF** when `temp < 29°C` and LED is currently ON
- Between 29–30°C: LED **holds current state** — no flickering at the threshold boundary

#### IR Slot Detection

Each IR sensor uses active-LOW logic with internal pull-up resistors:

```
IR reads 0 (LOW)  → slot is OCCUPIED (infrared beam broken by a car)
IR reads 1 (HIGH) → slot is FREE    (beam is intact)

available_slots = s1 + s2 + s3 + s4   (range: 0–4)
```

#### Ultrasonic Distance Measurement

A median filter with a buffer of 3 readings smooths out noise:

```
1. Send 10 µs HIGH pulse on TRIG
2. Measure echo duration with time_pulse_us()
3. distance = (duration × 0.0343) / 2  cm
4. Discard readings outside 2–150 cm range
5. If no valid reading for 1.5 s → set last_distance_cm = None
```

---

### 4.2 Bridge Script (`bridge.py`)

`bridge.py` runs on a laptop/PC and connects the ESP32 to Telegram and Blynk. It uses Python `threading` to run the Blynk polling loop in the background while the Telegram bot handles commands asynchronously.

**Key responsibilities:**
- Poll ESP32 `/status` endpoint every 5 seconds and push changed values to Blynk virtual pins
- Listen for Blynk gate pin changes and relay open/close commands to the ESP32
- Handle all Telegram bot commands and translate them into ESP32 HTTP requests
- Normalize `-1` sentinel values (returned when sensors are not ready) to `None` for clean display

---

### 4.3 Web Server

The ESP32 hosts a single-page HTTP server on port 8080. The dashboard uses JavaScript `fetch()` to communicate with the server without page redirects or full reloads:

- Page **loads once** and never navigates away — all updates happen in-place
- Status data is polled from `/status` every 5 seconds and rendered into DOM elements
- Button clicks call `cmd()` which fetches the action URL then calls `update()` to refresh the display
- All action routes return plain `OK` text — no redirects, no full page rebuilds
- `Access-Control-Allow-Origin: *` header prevents browser CORS fetch blocks
- JSON is built by string concatenation to avoid MicroPython `.format()` double-brace issues

---

## 5. IoT Integration

### 5.1 Telegram Bot

| Command | Description |
|---|---|
| `/start` | Shows the list of all available commands |
| `/status` | Returns full system status: slots, temp, humidity, gate, LED state and mode |
| `/slots` | Returns available slot count in `X / 4` format |
| `/temp` | Returns current temperature and humidity readings |
| `/open` | Sends open gate command to ESP32 |
| `/close` | Sends close gate command to ESP32 |
| `/led_on` | Turns LED on in MANUAL mode |
| `/led_off` | Turns LED off in MANUAL mode |
| `/led_auto` | Switches LED to AUTO temperature-based mode |

### 5.2 Web Dashboard

Accessible at `http://<ESP32_IP>:8080` from any browser on the same network.

**Displays:**
- Available slots (color-coded: green = available, red = full)
- Temperature and humidity
- Gate status (OPEN / CLOSED)
- LED status and current mode (MANUAL / AUTO)

**Controls:**
- Open Gate / Close Gate
- LED ON / LED OFF / LED AUTO

### 5.3 Blynk App

| Virtual Pin | Widget | Function |
|---|---|---|
| `V0` | Button | Gate control: `1` = Open, `0` = Close. Bridge reads and relays to ESP32. |
| `V1` | Value Display | Temperature in °C. Updated when value changes. |
| `V4` | Value Display | Available slot count. Updated when slots change. |
| `V5` | LED Indicator | LED state: `1` = ON, `0` = OFF. Updated when LED state changes. |

The Blynk loop uses a last-value cache for each pin and only sends an update request when the value actually changes, reducing unnecessary API calls and avoiding rate limits.

---

## 6. Working Process

### 6.1 System Boot Sequence

1. ESP32 powers on and initializes all pins and peripherals
2. LCD displays `System Start / Please wait`
3. Gate servo is commanded to CLOSED position (0°)
4. Built-in LED is turned off
5. All async tasks are created and scheduled by `uasyncio`
6. `wifi_manager()` connects to the configured SSID
7. Once WiFi is established, `web_server()` starts the HTTP server on port 8080
8. LCD updates to show `WiFi Connected` and the assigned IP address
9. System enters normal operation — all tasks run concurrently

### 6.2 Vehicle Entry Flow

```
Vehicle approaches
       │
       ▼
Ultrasonic < 15 cm?
       │ YES (×3 consecutive)
       ▼
Slots available?
  ├── NO  → Gate stays CLOSED
  └── YES → Gate OPENS (servo 90°)
              │
              ▼
         Vehicle enters → IR sensor reads LOW → slots count decreases
              │
              ▼
         Vehicle clears gate area (distance > 20 cm, ×3 consecutive, hold ≥ 3s)
              │
              ▼
         Gate CLOSES (servo 0°)
```

### 6.3 LED Control Flow

```
User presses LED ON / LED OFF
       │
       ▼
led_mode = 'MANUAL'
LED set immediately
AUTO loop skipped entirely
LED holds state until user presses another button

───────────────────────────────────

User presses LED AUTO
       │
       ▼
led_mode = 'AUTO'
       │
Every 250 ms:
  temp > 30°C AND LED is OFF → turn ON
  temp < 29°C AND LED is ON  → turn OFF
  29°C ≤ temp ≤ 30°C         → hold current state (deadband)
```

---

## 7. Challenges Faced

### 7.1 Memory Management on ESP32

Building large HTML strings caused `MemoryError` crashes that resulted in the web dashboard loading without buttons.

**Solution:**
- Replaced large triple-quoted HTML with compact string concatenation
- Called `gc.collect()` before building any HTML response
- Moved JSON building to a dedicated `build_status_json()` function
- Removed heavy CSS effects that added unnecessary string length

### 7.2 JSON Parsing Errors from `/status`

`bridge.py` repeatedly received `Expecting value: line 1 column 66` JSON parse errors.

**Root cause:** MicroPython's `.format()` with double-brace escaping `{{}}` produced malformed JSON, and `led_mode` was missing string quotes around its value.

**Solution:** Built JSON response through plain string concatenation with explicit quote characters — no `.format()` involved.

### 7.3 LED AUTO Mode Overriding Manual OFF

When the user pressed LED OFF, the LED would turn back on within 250 ms because `task_sensors()` was running the AUTO block unconditionally.

**Solution:** Check `led_mode` strictly before any LED operation in the AUTO block. Implemented deadband hysteresis of 1°C so the LED does not toggle when temperature hovers at the threshold.

### 7.4 Web Dashboard Buttons Disappearing

After several auto-reloads, the dashboard buttons would disappear due to incomplete HTML responses caused by low memory during rebuild.

**Solution:** Switched from meta-refresh page reloads to JavaScript `fetch()` polling. The full HTML is only built and sent once on initial page load — subsequent data updates only hit the lightweight `/status` JSON endpoint.

### 7.5 IP Address Mismatch

The bridge and browser were connecting to stale IP addresses from previous sessions since the ESP32 gets a new DHCP lease each boot.

**Solution:** Always check the serial monitor for the current IP printed at boot. Long-term fix: configure a static DHCP reservation on the router for the ESP32 MAC address.

### 7.6 IR Sensors False Positives

All four IR sensors triggered occupancy even with no cars present.

**Root causes:** Sensitivity potentiometer set too high, ambient infrared light interference, floating pins on disconnected sensors.

**Solution:** Adjust the blue potentiometer on each IR module until it only triggers reliably within range. Shield sensors from direct sunlight.

---

## 8. Future Improvements

### 8.1 Short-term

- Add a buzzer for audible full-parking alerts
- Display individual slot occupancy map on the web dashboard (slot 1, 2, 3, 4 separately)
- Add EEPROM or flash storage to persist slot state across reboots
- Add authentication to the Telegram bot so only authorized users can send commands
- Add a camera module to capture vehicle license plates on entry

### 8.2 Long-term

- Replace DHT11 with DHT22 for higher accuracy readings
- Add a second ultrasonic sensor at the exit to track vehicle departures independently
- Implement MQTT protocol instead of HTTP polling for lower latency cloud updates
- Develop a dedicated mobile app with real-time WebSocket updates
- Integrate a payment gateway for automated fee collection at the gate
- Add solar panel power supply with battery backup for off-grid deployment

### 8.3 Scalability

The current design supports 4 parking slots. Scaling to larger facilities would require:

- Multiple ESP32 nodes per zone connected via MQTT to a central broker
- A backend server (Raspberry Pi or cloud VM) aggregating data from all nodes
- A relational database storing historical occupancy, entry/exit timestamps, and revenue
- A public-facing web application showing zone maps and real-time availability counts

---

## 9. Conclusion

The Smart IoT Parking Management System successfully demonstrates a complete end-to-end IoT solution running on a resource-constrained embedded platform. All mandatory hardware components are integrated and functional: the ultrasonic sensor triggers automatic gate control, four IR sensors track individual slot occupancy, the servo operates the physical gate barrier, the DHT11 provides environmental monitoring, and both the TM1637 and I2C LCD show live system status.

All three IoT platforms are operational. The Telegram bot provides command-line control with real-time status reporting. The web dashboard delivers a single-page interface that updates without page reloads, solving memory constraints that caused earlier instability. The Blynk integration via `bridge.py` synchronizes gate control and sensor data in real time.

The project encountered and resolved several practical embedded systems challenges including memory management, JSON serialization bugs, sensor noise, and platform synchronization — each leading to a more robust and production-ready design.

---

*Smart IoT Parking Management System — Group Project Report*
