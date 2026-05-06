/*
 * LightControl — Fully Integrated Smart Controller
 * ================================================
 */

#include <WiFi.h>
#include <WebServer.h>
#include <Adafruit_NeoPixel.h>
#include <Wire.h>
#include <LiquidCrystal_I2C.h>

// ── WiFi Credentials ──────────────────────────────────────────
const char* WIFI_SSID = "Zenk1k0";
const char* WIFI_PASS = "092567088";

// ── Pins & Hardware ───────────────────────────────────────────
#define LED_PIN     13    
#define LDR_PIN     34    
#define LED_COUNT   24
Adafruit_NeoPixel ring(LED_COUNT, LED_PIN, NEO_GRB + NEO_KHZ800);
LiquidCrystal_I2C lcd(0x27, 16, 2); 
WebServer server(80);

// ── Thresholds ────────────────────────────────────────────────
#define THRESH_DARK    800   // Correct: Low value = Dark
#define THRESH_SUNNY   3000  // Correct: High value = Sunny
#define HYSTERESIS     150   
#define LDR_INTERVAL   500   

// ── Global State ──────────────────────────────────────────────
String currentMode     = "STARTUP";
String lightLabel      = "---";
int    rawLDR          = 0;
int    lastRawLDR      = 0;
int    autoBrightness  = 150;
bool   manualOverride  = false;
bool   rainbowActive   = false;
int    rainbowHue      = 0;
unsigned long lastLDRRead = 0;

// ══════════════════════════════════════════════════════════════
// SMART LDR LOGIC
// ══════════════════════════════════════════════════════════════

void readLDRAndAdjust() {
  int currentRead = analogRead(LDR_PIN);
  
  if (abs(currentRead - lastRawLDR) > HYSTERESIS) {
    rawLDR = currentRead;
    lastRawLDR = rawLDR;
    String prevLabel = lightLabel;
    
    // CORRECTED LOGIC: < is DARK, > is SUNNY
    if (rawLDR < THRESH_DARK)       lightLabel = "SUNNY";
    else if (rawLDR > THRESH_SUNNY)  lightLabel = "DARK";
    else                             lightLabel = "NORMAL";

    if (lightLabel != prevLabel) {
      manualOverride = false; 
      
      if (lightLabel == "SUNNY") {
        currentMode = "AUTO-OFF";
        ledsOff();
      } 
      else if (lightLabel == "DARK") {
        currentMode = "AUTO-ON";
        autoBrightness = 255;
        ledsWhite();
      }
      
      ring.setBrightness(autoBrightness);
      updateLCD();
      Serial.printf("[LDR] %s (%d) | Mode: %s\n", lightLabel.c_str(), rawLDR, currentMode.c_str());
    }
  }
}

// ══════════════════════════════════════════════════════════════
// LED & LCD HELPERS
// ══════════════════════════════════════════════════════════════

void ledsOff() { rainbowActive = false; ring.clear(); ring.show(); }
void ledsWhite() {
  rainbowActive = false;
  for(int i=0; i<LED_COUNT; i++) ring.setPixelColor(i, ring.Color(255, 255, 255));
  ring.show();
}

void updateLCD() {
  lcd.clear();
  lcd.setCursor(0, 0);
  lcd.print("M:"); lcd.print(currentMode);
  lcd.setCursor(0, 1);
  lcd.print("IP:"); lcd.print(WiFi.localIP().toString().substring(7)); // Shows last part of IP
  lcd.print(" B:"); lcd.print(autoBrightness);
}

void updateRainbow() {
  for (int i = 0; i < LED_COUNT; i++) {
    int pixelHue = rainbowHue + (i * 65536L / LED_COUNT);
    ring.setPixelColor(i, ring.gamma32(ring.ColorHSV(pixelHue)));
  }
  ring.show();
  rainbowHue += 256;
}

// ══════════════════════════════════════════════════════════════
// WEB SERVER
// ══════════════════════════════════════════════════════════════

void applyMode(String mode) {
  mode.toUpperCase();
  currentMode = mode;
  manualOverride = true; 
  ring.setBrightness(autoBrightness);

  if (mode == "OFF") ledsOff();
  else if (mode == "WHITE") ledsWhite();
  else if (mode == "RED") { rainbowActive = false; for(int i=0; i<LED_COUNT; i++) ring.setPixelColor(i, ring.Color(255, 0, 0)); }
  else if (mode == "GREEN") { rainbowActive = false; for(int i=0; i<LED_COUNT; i++) ring.setPixelColor(i, ring.Color(0, 255, 0)); }
  else if (mode == "BLUE") { rainbowActive = false; for(int i=0; i<LED_COUNT; i++) ring.setPixelColor(i, ring.Color(0, 0, 255)); }
  else if (mode == "RAINBOW") { rainbowActive = true; rainbowHue = 0; }

  if (!rainbowActive) ring.show();
  updateLCD();
  server.send(200, "text/plain", "OK");
}

void handleGesture() {
  if (server.hasArg("mode")) applyMode(server.arg("mode"));
  else server.send(400, "text/plain", "No mode");
}

// ══════════════════════════════════════════════════════════════
// SETUP & LOOP
// ══════════════════════════════════════════════════════════════

void setup() {
  Serial.begin(115200);
  ring.begin();
  ring.show();

  Wire.begin(21, 22);
  lcd.init();
  lcd.backlight();
  lcd.print("WiFi Connect...");

  WiFi.begin(WIFI_SSID, WIFI_PASS);
  while (WiFi.status() != WL_CONNECTED) { delay(500); Serial.print("."); }

  // This part ensures the IP stays visible for 5 seconds on boot
  lcd.clear();
  lcd.print("READY! IP:");
  lcd.setCursor(0, 1);
  lcd.print(WiFi.localIP());
  Serial.print("Controller IP: ");
  Serial.println(WiFi.localIP());
  delay(5000); 

  server.on("/gesture", handleGesture);
  server.begin();
  readLDRAndAdjust();
}

void loop() {
  server.handleClient();
  if (millis() - lastLDRRead > LDR_INTERVAL) {
    lastLDRRead = millis();
    readLDRAndAdjust();
  }
  if (rainbowActive) updateRainbow();
}